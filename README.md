# ⚽ Copa de Figurinhas — versão Vercel + Postgres (Neon)

Mesma aplicação de antes, mas agora ela **não usa arquivo local**: todas as figurinhas
(nome, posição e foto) ficam salvas num banco de dados **Postgres (Neon)**, que o Vercel
oferece de graça. Assim os dados não se perdem.

## 📁 Arquivos

```
copa-vercel/
├── api/
│   └── index.py        ← a aplicação inteira (backend + telas)
├── requirements.txt    ← dependências (Flask + psycopg2)
└── vercel.json         ← diz ao Vercel para mandar tudo para o app
```

> Tudo (visual + lógica) está dentro de `api/index.py`. Foi feito assim de propósito:
> o Vercel costuma ter problema para empacotar pastas de templates, então deixar num
> arquivo só evita erros.

---

## 🚀 Passo a passo para publicar (grátis)

### Parte 1 — Subir o projeto no Vercel

A forma mais fácil, sem usar terminal, é pelo **GitHub**:

1. Crie uma conta no **github.com** (se não tiver).
2. Crie um repositório novo (botão **New** → dê um nome, ex.: `copa-figurinhas` → **Create**).
3. Na página do repositório, clique em **Add file → Upload files** e arraste os arquivos
   desta pasta. **Importante:** mantenha a pasta `api` com o `index.py` dentro dela
   (você pode arrastar a pasta `api` inteira). Confirme com **Commit changes**.
4. Entre em **vercel.com**, crie conta (pode usar “Continuar com GitHub”).
5. No painel do Vercel: **Add New… → Project**, escolha o repositório `copa-figurinhas`
   e clique em **Deploy**. Espere terminar.

> Ele vai publicar, mas ainda **vai dar erro ao salvar** até você conectar o banco (Parte 2).

### Parte 2 — Criar o banco de dados Neon (Postgres)

1. No painel do seu projeto no Vercel, abra a aba **Storage**.
2. Clique em **Create Database** → escolha **Postgres (Neon)** → **Continue**.
3. Aceite o plano **Free**, escolha uma região (ex.: a mais próxima do Brasil) e crie.
4. Quando perguntar, **conecte o banco a este projeto**. Isso adiciona automaticamente
   a variável `DATABASE_URL` ao seu projeto. (A tabela é criada sozinha no primeiro envio.)

### Parte 3 — Definir a senha do professor

1. Ainda no projeto, vá em **Settings → Environment Variables**.
2. Adicione duas variáveis:
   - Nome: `SENHA_PROFESSOR`  | Valor: *a senha que você quiser*
   - Nome: `SECRET_KEY`       | Valor: *um texto aleatório longo qualquer*
3. Salve.

### Parte 4 — Publicar de novo

Vá na aba **Deployments**, abra o deploy mais recente (menu “…”) e clique em **Redeploy**.
Isso faz o app já subir com o banco e a senha configurados.

✅ Pronto! Seu site fica no ar num endereço tipo `https://copa-figurinhas.vercel.app`.
Compartilhe esse link com a turma. Para o painel, é o botão **🔒 Área do professor**.

---

## 💾 Backup / ver os dados
Os dados ficam no Neon. No Vercel, aba **Storage → Open in Neon** abre um painel onde dá
para ver a tabela `figurinhas` e exportar. Você também pode apagar figurinhas pelo botão
“Remover” no painel do professor.

## 🔒 Privacidade (atividade com menores)
Como envolve fotos de alunos, vale avisar os responsáveis / ter autorização de imagem da
escola, manter o link só com a turma, e apagar as figurinhas ao fim da atividade. A senha
protege o painel, mas é uma proteção simples, adequada a uma atividade escolar.

## ✏️ Quer mudar algo?
Tudo está em `api/index.py`:
- **Turmas:** procure por `<option value="8º ano">` (dentro do template `index.html`).
- **Posições:** edite a lista `POSICOES` lá no início do arquivo.
- **Cores das posições:** procure por `--pos-goleiro`, `--pos-zagueiro`, etc.

## ⚠️ Observações do Vercel
- O banco gratuito “dorme” quando fica parado; o **primeiro** acesso depois de um tempo
  pode demorar alguns segundos a mais (normal).
- O envio é limitado a ~4,5 MB por requisição, mas as fotos já são reduzidas no celular
  do aluno (ficam bem pequenas), então não tem problema.

---

### (Opcional) Publicar pelo terminal, sem GitHub
Se preferir e tiver o Node instalado:
```bash
npm i -g vercel
cd copa-vercel
vercel
```
Depois conecte o banco Neon e configure as variáveis pelo painel (Partes 2 a 4 acima).
