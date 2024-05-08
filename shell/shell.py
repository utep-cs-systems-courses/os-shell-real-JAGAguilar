#! /usr/bin/python3


import re
import os
import sys

# Function to print prompt string
def print_prompt():
    prompt = os.getenv('PS1', '$ ')
    sys.stdout.write(prompt)
    sys.stdout.flush()

def find_exec_path(command):
    paths = os.getenv('PATH').split(':')
    for path in paths:
        cmd_path = os.path.join(path, command)
        if os.path.exists(cmd_path):
            return cmd_path
    return command

def get_executables_and_operators(command):
    cmdStr= command.split(' ') #split the command on whitespace
    execs = []
    operators = []
    pattern = re.compile(r'\s*([\|<>;])\s*', re.IGNORECASE) #all operators to look for
    for part in cmdStr:
        if pattern.match(part):#if operator add to operator list
            operators.append(part)
        else:
            execs.append(part)#else add to execs
    return execs, operators

def handle_input_redirect(cmd, filename):
    if not os.path.isfile(filename):
        sys.stderr.write(f'Error: File not found: {filename}\n')
        return
    fd = os.open(filename, os.O_RDONLY)
    read_pipe, write_pipe = os.pipe()

    # fork
    pid = os.fork()

    if pid == 0: # child
        # close write pipe
        os.close(write_pipe)
        
        # duplicate read pipe to stdin
        os.dup2(read_pipe, sys.stdin.fileno())

        # close original read pipe
        os.close(read_pipe)

        # execute command
        exc, *args = cmd.split(" ")
        path = find_exec_path(exc)
        os.execve(path, [path] + args, os.environ)
    
    else: # parent
        # close read pipe
        os.close(read_pipe)

        # read from file and write to pipe
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            os.write(write_pipe, chunk)

        # close file descriptor
        os.close(fd)
        os.close(write_pipe)

        # wait for child process to finish
        os.waitid(os.P_PID, pid, os.WEXITED)


def handle_output_redirect(cmd, filename):
    fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    read_pipe, write_pipe = os.pipe()

    # fork
    pid = os.fork()

    if pid == 0: # child
        # close read pipe
        os.close(read_pipe)

        # duplicate write pipe to stdout
        os.dup2(write_pipe, sys.stdout.fileno())

        # close original write pipe
        os.close(write_pipe)

        # execute command
        exc, *args = cmd.split(" ")
        path = find_exec_path(exc)
        os.execve(path, [path] + args, os.environ)
    
    else: # parent
        # close write pipe
        os.close(write_pipe)

        # read from pipe and write to file
        while True:
            chunk = os.read(read_pipe, 4096)
            if not chunk:
                break
            os.write(fd, chunk)

        # close file descriptor
        os.close(fd)
        os.close(read_pipe)

        # wait for child process to finish
        os.waitid(os.P_PID, pid, os.WEXITED)

def handle_pipe(exec1, exec2):
    read_pipe, write_pipe = os.pipe()

    # fork
    pid = os.fork()

    if pid == 0: # child
        # close write pipe
        os.close(write_pipe)

        # duplicate read pipe to stdin
        os.dup2(read_pipe, sys.stdin.fileno())

        # close original read pipe
        os.close(read_pipe)

        # execute command
        exc, *args = exec2.split(" ")
        path = find_exec_path(exc)
        os.execve(path, [path] + args, os.environ)
    
    else: # parent
        # close read pipe
        os.close(read_pipe)

        # duplicate write pipe to stdout
        os.dup2(write_pipe, sys.stdout.fileno())

        # close original write pipe
        os.close(write_pipe)

        # execute command
        exc, *args = exec1.split(" ")
        path = find_exec_path(exc)
        os.execve(path, [path] + args, os.environ)

def run_command(command):
    executables, operators = get_executables_and_operators(command)
    # If no operators, just run the command
    if "cd" in executables:
        cdIndex = executables.index("cd")
        # Handle 'cd' command
        if cdIndex + 1 < len(executables):
            try:
                os.chdir(executables[cdIndex+1])
                executables.pop(cdIndex+1)
                executables.remove("cd")
            except FileNotFoundError:
                print("Directory not found.")
        else:
            print("Usage: cd <directory>")
    elif "echo" in executables:
        echoIndex = executables.index("echo")
        # Handle 'echo' command
        print(" ".join(executables[echoIndex+1:]))
        executables = executables[echoIndex:]
    elif "pwd" in executables:
        # Handle 'pwd' command
        print(os.getcwd())
        executables.remove("pwd")
    else:
        pid = os.fork()
        if pid == 0:
            os.execv(find_exec_path(executables[0]), executables)
        else:
            os.waitpid(pid, 0)
    
    # Handle operators (left to right)
    for i, operator in enumerate(operators):
        if operator == '|':
            pid = os.fork()
            if pid == 0:
                handle_pipe(executables[i], executables[i+1])
            else:
                os.waitid(os.P_PID, pid, os.WEXITED)
        elif operator == '<':
            handle_input_redirect(executables[i], executables[i+1])
        elif operator == '>':
            handle_output_redirect(executables[i], executables[i+1])
        else:
            pid = os.fork()
            if pid == 0:
                os.execv(find_exec_path(executables[0]), executables)
            else:
                os.waitpid(pid, 0)


def main():
    # Main shell loop
    while True:
        print_prompt()
        user_input = sys.stdin.readline().rstrip('\n')  # Read user input
        # Parse input
        if user_input == 'exit':
            break
        elif user_input == '':
            pass
        else:
            run_command(user_input)

if __name__ == '__main__':
    main()

