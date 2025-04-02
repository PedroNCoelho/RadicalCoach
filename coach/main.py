from source.coach_cli import *

if __name__ == "__main__":
    if os.path.exists("../shared/coach_ans.txt"):
        os.remove("../shared/coach_ans.txt")
    conn  = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    conn.bind(("coach",coach_port))
    cli = CoachCLI(conn)
    while True:
        # blocks until a message is sent
        cli.wait_and_process_message()
