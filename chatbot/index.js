//importa as bibliotecas necessárias
const { Client } = require('whatsapp-web.js'); //biblioteca principal para integrar com o whatsapp
const qrcode = require('qrcode-terminal'); //gera o qr code no terminal
const fs = require('fs'); //lida com arquivos
const path = require('path'); //manipula caminhos de arquivos
const { execFile } = require('child_process'); //permite executar scripts externos
const ffmpeg = require('fluent-ffmpeg'); //usado para análises de vídeo, como tempo de duração

const { MessageMedia } = require('whatsapp-web.js');

// ffmpeg.setFfprobePath("C:/ffmpeg/bin/ffprobe.exe");
ffmpeg.setFfprobePath("ffmpeg");  //ajuste o caminho conforme sua instalação

//inicializa o cliente do whatsapp
const client = new Client();

//armazena os estados dos usuários por número
let estadoUsuarios = {};

//caminhos para o interpretador python e o script principal
//const pythonPath = "C:/Users/Usuario/AppData/Local/Programs/Python/Python313/python.exe";
const pythonPath = "python3";
const pastaVideo = path.join("..","shared", 'videos_recebidos');
const scriptPath = path.join('..','shared','coach_facade.py');

//exibe o QR Code no terminal para autenticar o WhatsApp
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
});

//confirma que o bot está pronto
client.on('ready', () => {
    console.log("🤖 Bot RadicalCoach está online!");
});

//lógica principal: ouve mensagens recebidas
client.on('message', async (msg) => {
    const numero = msg.from; //número do usuário que enviou a mensagem
    const texto = msg.body.trim().toLowerCase(); //texto da mensagem em minúsculo
	
     console.log("esta no inicio")
    //se o usuário for novo ou ainda não começou, envia mensagem de boas-vindas
    if (!estadoUsuarios[numero]) {
        estadoUsuarios[numero] = { estado: "aguardando_confirmacao" };
        msg.reply(`🎯 *Bem-vindo ao RadicalCoach!* 🎯\n\nEstou aqui para te ajudar a evoluir nas suas manobras de forma inteligente! 🛹🔥\n\nDeseja começar escolhendo uma ação? (responda com *sim* ou *não*)`);
        return;
    }

    //se o usuário não quiser continuar
    if (texto === "não") {
        estadoUsuarios[numero] = null;
        msg.reply("Tudo bem! Quando quiser começar, digite *menu*.");
        return;
    }

    //reinicia o menu
    if (texto === "menu") {
        estadoUsuarios[numero] = { estado: "aguardando_confirmacao" };
        msg.reply(`🎯 *Bem-vindo ao RadicalCoach!* 🎯\n\nDeseja começar escolhendo uma ação? (responda com *sim* ou *não*)`);
        return;
    }


    //quando o usuário escolhe o esporte
    if (texto === "sim" && estadoUsuarios[numero]?.estado === "aguardando_confirmacao") {

            const esporteSelecionado = "skate"

            //chama select_sport no back
            execFile(pythonPath, [scriptPath, "select_sport", esporteSelecionado], (error) => {
                if (error) {
                    console.error("Erro ao selecionar esporte:", error);
                    msg.reply("❌ Erro ao selecionar o esporte.");
                    return;
                }

                //depois chama show_actions para esse esporte
                execFile(pythonPath, [scriptPath, "show_actions"], (error, stdout) => {
                    if (error) {
                        console.error("Erro ao buscar ações:", error);
                        msg.reply("❌ Erro ao buscar ações para o esporte.");
                        return;
                    }

                    try {
                        //extrai as ações de uma string com lista
                        const raw = stdout.toString().trim();
                        const match = raw.match(/\[\s*'([^']+)'(?:\s*,\s*'([^']+)')*\s*\]/g);

                        if (!match || match.length === 0) {
                            msg.reply("⚠️ Nenhuma ação encontrada.");
                            return;
                        }

                        const listaBruta = match[0]
                            .replace(/[\[\]']+/g, '')
                            .split(',')
                            .map(e => e.trim());

                        estadoUsuarios[numero] = {
                            estado: "escolhendo_acao",
                            esporte: esporteSelecionado,
                            acoes: listaBruta
                        };

                        let textoFormatado = `🎯 *Ações disponíveis para ${esporteSelecionado}:*\n\n`;
                        listaBruta.forEach((acao, idx) => {
                            textoFormatado += `*${idx + 1}.* ${acao}\n`;
                        });
                        textoFormatado += "\nDigite o *número* da ação para selecionar.";
                        msg.reply(textoFormatado);

                    } catch (err) {
                        console.error("Erro ao processar ações:", err);
                        msg.reply("⚠️ Ocorreu um erro ao processar as ações.");
                    }
                });
            });
        return;
    }

    //quando o usuário escolhe a ação
    if (estadoUsuarios[numero]?.estado === "escolhendo_acao" && !isNaN(texto)) {
        const index = parseInt(texto) - 1;
        const acoes = estadoUsuarios[numero].acoes;

        if (index >= 0 && index < acoes.length) {
            const acaoSelecionada = acoes[index];

            estadoUsuarios[numero] = {
                estado: "aguardando_video",
                esporte: estadoUsuarios[numero].esporte,
                acao: acaoSelecionada,
                indice: index,
                acoes
            };

            // msg.reply(`✅ Você escolheu treinar *${acaoSelecionada}* no *${estadoUsuarios[numero].esporte}*!\n\n📹 Por favor, envie um vídeo de até *15 segundos* para continuarmos.`);
            msg.reply(`✅ Você escolheu treinar *${acaoSelecionada}* no *${estadoUsuarios[numero].esporte}*!\n\n`);
            
            // SEÇÃO ATUALMENTE MOCKADA, FALTA INTEGRAR!
            msg.reply("Esses são os movimentos dessa manobra:")
            const push_on_guide = '../shared/push_on_guide/'
            
            const media1 = MessageMedia.fromFilePath(push_on_guide+'prepare.png');
            await client.sendMessage(msg.from, media1, { caption: 'Preparação do Impulso' });
            
            const media2 = MessageMedia.fromFilePath(push_on_guide+'boost_f1.png');  
            await client.sendMessage(msg.from, media2, { caption: 'Início do Impulso' });
            
            const media3 = MessageMedia.fromFilePath(push_on_guide+'boost_f2.png');
            await client.sendMessage(msg.from, media3, { caption: 'Auge do Impulso' });
            
            const media4 = MessageMedia.fromFilePath(push_on_guide+'boost_f3.png');
            await client.sendMessage(msg.from, media4, { caption: 'Finalização do Impulso' });
            
            const media5 = MessageMedia.fromFilePath(push_on_guide+'recovery.png');
            await client.sendMessage(msg.from, media5, { caption: 'Recuperação dos pés' });

            msg.reply(`📹 Por favor, envie um vídeo de até *15 segundos* para continuarmos.`);
        } else {
            msg.reply("❌ Número inválido! Digite o número correspondente à ação desejada.");
        }
        return;
    }

    //quando o usuário envia o vídeo
    if (estadoUsuarios[numero]?.estado === "aguardando_video" && msg.hasMedia) {
	    // msg.reply("aguardando vídeo teste")
	    console.log("aguardando vídeo teste")
        //const pastaVideo = path.join("..","shared", 'video_buffer'); //pasta onde o vídeo será salvo
        const caminhoCompleto = path.join(pastaVideo, 'video.mp4'); //nome fixo do arquivo de vídeo

        try {
            //baixa o vídeo
            const media = await msg.downloadMedia();

            //cria a pasta se não existir
            if (!fs.existsSync(pastaVideo)) {
                fs.mkdirSync(pastaVideo, { recursive: true });
            }

            //salva o vídeo em formato base64 convertido para binário
            fs.writeFileSync(caminhoCompleto, Buffer.from(media.data, 'base64'));
            msg.reply("✅ Vídeo recebido com sucesso! Processando...");

            estadoUsuarios[numero].estado = "processando_video";

            //executa o processamento do vídeo
            execFile(pythonPath, [scriptPath, "process_video"], (error) => {
                if (error) {
                    console.error("Erro ao executar process_video:", error);
                    msg.reply("❌ Ocorreu um erro ao processar o vídeo. Tente novamente.");
                    return;
                }

                //executa a classificação da ação escolhida
                execFile(pythonPath, [scriptPath, "select_action", estadoUsuarios[numero].indice], (error2) => {
                    if (error2) {
                        console.error("Erro ao executar select_action:", error2);
                        msg.reply("❌ Erro ao gerar o feedback. Tente novamente.");
                        return;
                    }

                    //aguarda até que o arquivo de feedback seja gerado
                    const feedbackFile = path.join('..', 'shared/output' , 'feedback.txt');
                    let attempts = 0;

                    const checkFile = setInterval(() => {
                        if (fs.existsSync(feedbackFile)) {
                            const conteudo = fs.readFileSync(feedbackFile, 'utf8');
                            if (conteudo.trim().length > 0) {
                                clearInterval(checkFile);
                                msg.reply("✅ *Análise concluída!*\n\n📈 Aqui está seu feedback personalizado:\n\n" + conteudo);
                                estadoUsuarios[numero] = null;
                            }
                        }

                        attempts++;
                        if (attempts > 20) {
                            clearInterval(checkFile);
                            msg.reply("⚠️ Ocorreu um erro ao gerar o feedback. Tente novamente.");
                        }
                    }, 1000);
                });
            });

        } catch (err) {
            console.error("Erro ao salvar vídeo:", err);
            msg.reply("❌ Ocorreu um erro ao processar o vídeo. Tente novamente.");
        }
	// msg.reply("parou no return")
	console.log("parou no return")
        return;
    }
});

//inicia o cliente do whatsApp
client.initialize();











