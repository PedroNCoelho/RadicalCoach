import sys
import socket

class FileNotReadableError(Exception):
    def __init__(self,context):
        super().__init__(f"tried to read a non readable file in {context}")

coach_port = 2564

def return_read_lines(file):
    """
    helper function to concatenate multiple lines 
    from a readable file
    """
    ans =[]
    for line in file.readlines():
        ans.append(line)
    return ans

def process_and_close_file(file):
    """
    helper function that expect a function that receives a file
    after calling such function also close the file
    """
    if not file.readable():
        raise FileNotReadableError("process_and_close_file")
    answer = file.readlines()
    file.close()
    return answer


def read_answer_from_coach():
    """
    read a file written by the persistent process and 
    return the contents, note that appends to such file
    , by the peristent process, results in invalid data
    """
    try:
        file = open("coach_ans.txt", "r")
        return process_and_close_file(file)
    except:
        raise FileNotFoundError()

def wait_for_answer():
    """
    open and close an udp connection to the coach_process 
    """
    conn = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    _ = conn.sendto(b"OK",("localhost",coach_port))
    # wait until persistent process sends a message
    _ = conn.recv(8)
    return

def write_to_existing_file(file,cmd,args):
    """
    expect file to be written in append mode and to exist.
    this allows the persistent process to "mantain" a sequence
    of user interactions
    """
    file = open(file, "w") 
    if args:
        file.write(cmd + "," + args+ "\n")
    else:
        file.write(cmd+","+"\n")
    return

def write_to_non_existing_file(file, cmd, args):
    """
    expect file to be created.
    """
    file = open(file,"x")
    if args:
        file.write(cmd + " , " + args)
    else:
        file.write(cmd + " ")
    return

def send_to_coach(cmd,args):
    """
    this function executes the following workflow:
    -find the persistent process id
    -write the user interaction in coach_cmd_args.txt or create it if doesn't exist
    -initiate an udp connection to the persistent process  
    -wait for the persistent process to send a confirmation through the socket
    - parse and send an confirmation in cases of 'selection cmds' and a "big string"
     read from a txt file in cases of 'show cmds'
     """
    try:
        write_to_existing_file("coach_cmd_args.txt",cmd,args)
    except:
        write_to_non_existing_file("coach_cmd_args.txt",cmd,args)
    wait_for_answer()
    return read_answer_from_coach()

def parse_stdin():
    """
    helper function that parses
    cmd and args
    """
    args = ""
    for arg in sys.argv[2:]:
        args+=arg
    return (sys.argv[1],None if args == "" else args)
    
def send_to_stdout(coach_answer,fn=None):
    """
    helper function that allows a custom
    function to send user interaction through stdout
    """
    if fn is not None:
        fn(coach_answer)
        return
    print(coach_answer)

def process_command():
    """
    helper function to process command called by other processes
    """
    cmd, args = parse_stdin()
    coach_feedback = send_to_coach(cmd,args)
    send_to_stdout(coach_feedback)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("Uso: python skate_prototype.py [comando] [opcional: argumentos]")
        sys.exit(1)

    process_command()

