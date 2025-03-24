from .initializations import *

def format_error(msg):
    """
    how to format commands that errored
    """
    return "ERROR" + "," + msg

def format_success(msg):
    """
    how to format commands that completed successfully
    """
    return "OK" + "," + msg

def parse_facade():
    """
    read a file written by facade containing the last
    command and corresponding arguments
    """
    try:
        file = open("/shared/coach_cmd_args.txt", "r")
        if not file.readable():
            raise FileNotReadableError("parse_facade")
        # expect arguments to be "split" by " "(empty spaces)
        cmd, args = file.readline().split(",",1)
        args = args[:-1]
        return (cmd,args)
    except:
        FileNotFoundError("parse_facade")



class CoachCLI:
    def __init__(self,conn):
        self.sport_name = None
        self.coach = None
        self.landmarks_per_frame = None
        self.socket = conn

    def _reset_all(self):
        """
        Completely reset the current instance
        """
        self.sport_name = None
        self.coach = None
        self.landmarks_per_frame = None
        reset_folder(vb_f)
        reset_folder(proc_f)
        reset_folder(output_f)

    def _write_first_coach_answer(self,cmd,args):
        """
        create and write the command output after running it
        through a handler
        """
        file = open("/shared/coach_ans.txt","x")
        file.write(str(self._run(cmd,args)))
        file.close()
        return

    def _write_subsequent_coach_answer(self,cmd,args):
        """
        write the command output after running it
        through a handler
        """
        file = open("/shared/coach_ans.txt","w")
        file.write(str(self._run(cmd,args)))
        file.close()
        return

    def write_coach_answer(self,cmd,args):
        """
        given a command and possible arguments
        execute it.
        after execution the command can either error out or be successfull
        """
        try:
            self._write_first_coach_answer(cmd,args)
        except:
            self._write_subsequent_coach_answer(cmd,args)
        return

    def show_sports(self):
        """
        show every available sport provided by current coach instance
        """
        return format_success("Esportes disponíveis: skate")

    def select_sport(self, sport):
        """
        select a sport and if provided argument sport is not
        equal to the instance attribute sport, reset the current instance
        """
        if sport == "skate":
            if self.sport_name and self.sport_name != sport:
                self._reset_all()
            self.sport_name = sport
            self.coach = create_Coach(sport)
            if self.landmarks_per_frame is not None:
                self.coach.update_landmarks(self.landmarks_per_frame)
            # self.save_state()
            return format_success("Esporte selecionado")
        else:
            return format_error(INVALID_SPORT)

    def show_actions(self):
        """
        show actions for the user select sport
        validation happens elsewhere
        """
        if self.coach:
            # actions = self.coach.get_action_labels()
            # actions_collection = ""
            # for _, action in enumerate(actions):
            #     actions_collection+= ","+ str(action)
            actions_collection = str(self.coach.get_action_labels())
            return format_success(actions_collection)
        else:
            return format_error(MISSING_SPORT)

    def select_action(self, action_id):
        """
        compute feedback and return a path to it
        """
        action_id = int(action_id)
        if self.coach:
            actions = self.coach.get_action_labels()
            if 0 <= action_id < len(actions):
                # print("Executando análise para a ação '{}'...".format(actions[action_id]))
                self.coach.process_action(action_id)
                reset_folder(output_f)
                message = self.coach.generate_feedback(action_id)
                # self.save_state()
                return format_success(message)
            else:
                return format_error(INVALID_ACTION)
        else:
                return format_error(MISSING_SPORT)

    
    def process_video(self):
        print("Processando o novo vídeo...")
        reset_folder(proc_f)
        video_cap = cv2.VideoCapture(video_path)
        pose_tracker = mp_pose.Pose()
        proc_video = cv2.VideoWriter(proc_video_path, cv2.VideoWriter_fourcc(*'mp4v'),
                                     video_cap.get(cv2.CAP_PROP_FPS),
                                     (int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                      int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

        self.landmarks_per_frame = []
        with tqdm.tqdm(total=video_cap.get(cv2.CAP_PROP_FRAME_COUNT), position=0, leave=True) as pbar:
            while True:
                success, input_frame = video_cap.read()
                if not success:
                    break
                pose_landmarks, output_frame = get_frame_landmarks(input_frame, pose_tracker)
                self.landmarks_per_frame.append(pose_landmarks)
                proc_video.write(cv2.cvtColor(np.array(output_frame), cv2.COLOR_RGB2BGR))
                pbar.update()

        proc_video.release()
        pose_tracker.close()
        video_cap.release()

        if self.coach:
            self.coach.update_landmarks(self.landmarks_per_frame)

        return format_success("O vídeo foi processado com sucesso.")    
    
    
    def _run(self, command, args):
        """
        handler function for command execution
        """
        commands = {
            "show_sports": self.show_sports,
            "select_sport": self.select_sport,
            "show_actions": self.show_actions,
            "select_action": self.select_action,
            "process_video": self.process_video,
        }

        if command in commands:
            if args[0] != '':
                return commands[command](*args)
            else:
                return commands[command]()
        else:
            return format_error(INVALID_COMMAND)

    def wait_and_process_message(self):
        _,addr = self.socket.recvfrom(8)
        parsed = parse_facade()
        args = []
        
        if parsed is not None:
            cmd = parsed[0]
            args = parsed[1:]
            self.write_coach_answer(cmd,args)
            self.socket.sendto(b"OK",addr)
