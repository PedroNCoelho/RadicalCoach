from .action import *

class Coach():
    def __init__(self, actions, sport_name, proc_video_path, output_path):
        """
        Inicializa o Coach.
        :param actions: Lista de ações (Action)
        :param sport_name: Nome do esporte
        :param proc_video_path: Caminho do vídeo processado
        :param output_path: Caminho dos arquivos de saída
        """
        self.actions = actions
        self.sport_name = sport_name
        self.proc_video_path = proc_video_path
        self.output_path = output_path
        self.landmarks_arr = None  # Inicializa o array como None

    def update_landmarks(self, landmarks_arr):
        self.landmarks_arr = landmarks_arr

    def get_action_labels(self):
        """Retorna a lista de rótulos das ações que o Coach pode orientar."""
        return [action.label for action in self.actions]

    def process_action(self, action_id):
        """
        Executa a verificação de uma ação específica.
        :param action_id: Índice da ação na lista de actions
        """
        if self.landmarks_arr is None:
            raise ValueError("O vídeo ainda não foi processado.")

        if action_id < 0 or action_id >= len(self.actions):
            raise ValueError("ID da ação inválido.")

        action = self.actions[action_id]
        action.verify(self.landmarks_arr)  # Chama o método de verificação da Action


    def generate_feedback(self, action_id):
        """
        Cria um arquivo de feedback visualmente mais estruturado.
        """
        action = self.actions[action_id]
        feedback_text = "="*50 + "\n"
        feedback_text += f" AÇÃO ANALISADA: {action.label}\n"
        feedback_text += action.feedback+"\n"
        feedback_text += "="*50 + "\n\n"

        for movement in action.movements():
            feedback_text += f" Movimento: {movement.label}\n"
            feedback_text += f"    Feedback: {movement.get_feedback()}\n"
            feedback_text += "-"*50 + "\n"

        feedback_text += "\n Análise concluída!\n"

        feedback_path = os.path.join(self.output_path, "feedback.txt")

        with open(feedback_path, "w") as f:
            f.write(feedback_text)

        # Verificar se o arquivo foi salvo corretamente
        if os.path.exists(feedback_path):
            message = (f" Feedback salvo em: {feedback_path}")
        else:
            message = (" Erro: O feedback não foi gerado corretamente!")

        # chosen_movement = action.movements()[0]
        # print(f" Contabilizando em vídeo o movimento: {chosen_movement.label}")
        # video_with_counter(chosen_movement.get_name(), action.classification_per_frame)
        # print("\n Vídeo salvo em", output_video_path)

        return message


    # def generate_feedback(self, action_id):
    #     """
    #     Cria um arquivo de feedback no caminho de saída.
    #     """
    #     # feedback_text = "Feedback gerado com sucesso!"  # Placeholder
    #     action = self.actions[action_id]
    #     feedback_text = f"Ação: {action.label}\n"+action.feedback+"\n"
    #     for movement in action.movements():
    #         feedback_text += f"  Movimento: {movement.label}\n"
    #         feedback_text += f"    Feedback: {movement.get_feedback()}\n"

    #     feedback_path = os.path.join(self.output_path, "feedback.txt")

    #     with open(feedback_path, "w") as f:
    #         f.write(feedback_text)

    #     # Verificar se o arquivo foi salvo corretamente
    #     if os.path.exists(feedback_path):
    #         print(f"Feedback salvo em: {feedback_path}")
    #     else:
    #         print("Erro: O feedback não foi gerado corretamente!")

    #     chosen_moviment = action.movements()[0]
    #     print("Contabilizando em vídeo o movimento", chosen_moviment.label)
    #     video_with_counter(chosen_moviment.get_name(), action.classification_per_frame)
    #     print("\nVídeo salvo em", output_video_path)

    #     return feedback_path
