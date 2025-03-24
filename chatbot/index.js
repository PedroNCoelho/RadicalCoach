const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const ffmpeg = require('fluent-ffmpeg');

ffmpeg.setFfprobePath("ffmpeg");  //ajuste o caminho conforme sua instalação

const client = new Client();

let estadoUsuarios = {};
let timeoutUsuarios = {};

//diretório para salvar os vídeos
const pastaVideos = path.join("shared", 'videos_recebidos');

//cria a pasta se não existir
if (!fs.existsSync(pastaVideos)) {
	fs.mkdirSync(pastaVideos, { recursive: true });
}

//caminho do Python e do script de processamento
const pythonPath = "python3"
const scriptPath = path.join(__dirname, 'scripts', 'processar_video.py');

//função para resetar o estado do usuário após 15 minutos de inatividade
const resetarEstado = (numero) => {
	if (estadoUsuarios[numero]) {
		client.sendMessage(numero, "⌛ Sua sessão expirou por inatividade. Digite *menu* para recomeçar.");
	}
	delete estadoUsuarios[numero];
	delete timeoutUsuarios[numero];
};

//função para reiniciar o temporizador de inatividade
const reiniciarTimeout = (numero) => {
	if (timeoutUsuarios[numero]) {
		clearTimeout(timeoutUsuarios[numero]);
	}
	timeoutUsuarios[numero] = setTimeout(() => {
		resetarEstado(numero);
	}, 15 * 60 * 1000); //15 minutos
};

//esportes e ações
const esportes = {
	"Skate": ["Remada", "Ficar em pé"]
};

client.on('qr', (qr) => {
	console.log('Escaneie este QR Code para conectar:');
	qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
	console.log('Cliente conectado com sucesso!');
});

client.on('message', async (msg) => {
	const numero = msg.from;
	const texto = msg.body.trim().toLowerCase();

	reiniciarTimeout(numero); //sempre reinicia o tempo ao receber mensagem


	//se o usuário enviar um vídeo
	if (msg.hasMedia) {
		const media = await msg.downloadMedia();

		if (estadoUsuarios[numero]?.estado === "aguardando_video") {
			//criar nome do arquivo
			const esporte = estadoUsuarios[numero].esporte;
			const acao = estadoUsuarios[numero].acao;
			const timestamp = Date.now();
			const nomeArquivo = `${numero}_${esporte}_${acao}_${timestamp}.mp4`;

			//caminho do arquivo
			const caminhoArquivo = path.join(pastaVideos, nomeArquivo);

			//salvar o vídeo
			fs.writeFile(caminhoArquivo, media.data, { encoding: 'base64' }, (err) => {
				if (err) {
					console.error("Erro ao salvar o vídeo:", err);
					msg.reply("❌ Ocorreu um erro ao salvar o vídeo. Tente novamente.");
				} else {
					//verificar a duração do vídeo
					ffmpeg.ffprobe(caminhoArquivo, (erro, metadata) => {
						if (erro) {
							console.error("Erro ao verificar o vídeo:", erro);
							msg.reply("⚠️ Não foi possível processar o vídeo. Tente novamente.");
							fs.unlinkSync(caminhoArquivo); //remove o arquivo inválido
							return;
						}

						const duracaoVideo = metadata.format.duration;

						//se o vídeo tiver mais de 15 segundos, rejeita e não reseta o estado do usuário
						if (duracaoVideo > 15) {
							msg.reply("❌ O vídeo excede o limite de 15 segundos. Envie um vídeo menor!");
							fs.unlinkSync(caminhoArquivo); //remove o arquivo inválido
							return;
						}

						//se o vídeo for válido, chamar o script Python para processar
						execFile(pythonPath, [scriptPath, caminhoArquivo], (error, stdout, stderr) => {
							if (error) {
								console.error(`Erro ao executar o script Python: ${error}`);
								msg.reply("❌ Erro ao processar o vídeo. Tente novamente mais tarde.");
								return;
							}

							try {
								//mensagem genérica de feedback
								msg.reply("✅ Vídeo analisado com sucesso! Aqui está seu feedback: Continue treinando, você está indo bem! 🏆");
							} catch (err) {
								console.error("Erro ao interpretar retorno do script:", err);
								msg.reply("⚠️ Ocorreu um erro ao interpretar os dados do vídeo.");
							}
						});
					});
				}
			});
		} else {
			msg.reply("❌ Você precisa primeiro selecionar um esporte e uma ação! Digite *menu* para começar.");
		}
		return;
	}

	//menu inicial - Escolher esporte
	if (texto === "menu" || !estadoUsuarios[numero]) {
		estadoUsuarios[numero] = { estado: "escolhendo_esporte" };

		let menu = `🏆 *Bem-vindo ao SkateCoach!* 🏆\n`;
		menu += `Estou aqui para te ajudar a melhorar suas manobras! 🛹🔥\n\n`;
		menu += `*Escolha um esporte para começar:*\n`;

		let index = 1;
		for (let esporte in esportes) {
			menu += `*${index}.* ${esporte}\n`;
			index++;
		}

		msg.reply(menu + "\nDigite o número do esporte para continuar.");
		return;
	}

	//se o usuário está escolhendo um esporte
	if (estadoUsuarios[numero].estado === "escolhendo_esporte") {
		const esporteEscolhido = Object.keys(esportes)[parseInt(texto) - 1];

		if (esporteEscolhido) {
			estadoUsuarios[numero] = { estado: "escolhendo_acao", esporte: esporteEscolhido };

			let resposta = `🎯 *Você escolheu ${esporteEscolhido}!* 🎯\n\n`;
			resposta += `Agora, escolha a ação que deseja treinar:\n`;

			esportes[esporteEscolhido].forEach((acao, index) => {
				resposta += `*${index + 1}.* ${acao}\n`;
			});

			resposta += `\nDigite o número da ação para continuar ou digite *Voltar* para escolher outro esporte.`;
			msg.reply(resposta);
		} else {
			msg.reply("❌ Opção inválida! Digite um número correspondente a um esporte.");
		}
		return;
	}

	//se o usuário quer voltar à seleção de esporte
	if (texto === "voltar" && estadoUsuarios[numero].estado === "escolhendo_acao") {
		estadoUsuarios[numero] = { estado: "escolhendo_esporte" };

		let menu = `🔄 *Você voltou ao menu de esportes!*\n\n`;
		menu += `Escolha um esporte para começar:\n`;

		let index = 1;
		for (let esporte in esportes) {
			menu += `*${index}.* ${esporte}\n`;
			index++;
		}

		msg.reply(menu + "\nDigite o número do esporte para continuar.");
		return;
	}

	//se o usuário está escolhendo uma ação
	if (estadoUsuarios[numero].estado === "escolhendo_acao") {
		const esporte = estadoUsuarios[numero].esporte;
		const acaoEscolhida = esportes[esporte][parseInt(texto) - 1];

		if (acaoEscolhida) {
			estadoUsuarios[numero] = { estado: "aguardando_video", esporte, acao: acaoEscolhida };

			msg.reply(`✅ Você escolheu treinar *${acaoEscolhida}* no *${esporte}*!\n\n🎥 Agora, envie um vídeo de até *15 segundos* para que possamos analisá-lo!\n\nDigite *Voltar* para escolher outra ação.`);
		} else {
			msg.reply("❌ Opção inválida! Digite um número correspondente a uma ação ou digite *Voltar* para escolher outro esporte.");
		}
		return;
	}
	msg.reply("❌ Comando não reconhecido! Digite *menu* para ver as opções.");
	//caso o usuário envie algo não reconhecido
	if (texto == "") {
		msg.reply("demorou")
	}
});

client.initialize();



