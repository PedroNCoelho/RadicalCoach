import os

shared_f = '../shared'
vb_f = os.path.join(shared_f, 'videos_recebidos')
output_f = os.path.join(shared_f, 'output')
reference_csvs_f = 'reference_csvs'
proc_f = 'processed'

video_name = 'video.mp4'
# csv_name = 'output.csv'
# output_video_name = 'output.mp4'
proc_video_name = 'proc.mp4'
cmd_args_name = 'coach_cmd_args.txt'
coach_ans_name = 'coach_ans.txt'

video_path = os.path.join(vb_f, video_name)
# csv_path = os.path.join(output_f, csv_name)
# output_video_path = os.path.join(shared_f, output_f, output_video_name)
proc_video_path = os.path.join(proc_f, proc_video_name)
cmd_args_path = os.path.join(shared_f, cmd_args_name)
coach_ans_path = os.path.join(shared_f, coach_ans_name)


coach_port = 2564
INVALID_COMMAND="O comando digitado não é válido."
INVALID_ACTION="A ação escolhida não é válida."
MISSING_SPORT="Você precisa selecionar um esporte primeiro."
INVALID_SPORT="O esporte informado não é válido."