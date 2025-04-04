botão com a logo do Discord ao lado esquerdo do botão de iniciar com uma bolinha verde/vermelha
ao lado da logo pra indicar se o bot ta on ou off
uma boolean armazenando o status do Bot

o bot vai ficar dentro da pasta da cluster então quando selecionar uma pasta:
o botão de ir pra area do bot aparece
algum codigo vai checar pra ver se achar uma pasta bot/ dentro do cluster e um index js pra iniciar
se nao achar o a bolinha fica preta indicando um erro no bot e ao clicar no botao vai so aparecer um dialog
mostrando o erro que deu

se achar o bot de boa ao clicar no botao do discord
vai passar para uma area com um terminal que mostra o out do bot e uma area de in para executar comandos
do bot.
botoes em cima para reiniciar/iniciar/desligar o bot, e um botao que abre a pasta do bot para configuração

1. começar entendendo a logica para criar o botão -- botão criado e colocado
2. logo do discord, bolinha com cor verde vermelha e preta -- o sistema da bolinha precisa ser pensado melhor
3. entender como funciona a função de reconhecer a cluster
4. criar uma classe que vai ficar todas as info do discord
5. procurar uma especie de childprocces em python pra rodar o codigo node do bot