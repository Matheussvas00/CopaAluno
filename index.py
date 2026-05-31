"""
Copa de Figurinhas - versao para Vercel + Postgres (Neon).
Tudo num arquivo so: backend + templates embutidos (evita problemas de
empacotamento de pastas no Vercel).

Configuracoes ficam em Variaveis de Ambiente no painel da Vercel:
  - DATABASE_URL     -> injetada automaticamente ao conectar o Neon
  - SENHA_PROFESSOR  -> a senha do painel (defina voce)
  - SECRET_KEY       -> um texto aleatorio longo (defina voce)
"""
import os
from datetime import datetime
from functools import wraps

import psycopg2
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from jinja2 import DictLoader

# ===================== CONFIGURACOES =====================
SENHA_PROFESSOR = os.environ.get("SENHA_PROFESSOR", "copa2026")
SECRET_KEY = os.environ.get("SECRET_KEY", "troque-este-texto-por-algo-aleatorio-grande")
POSICOES = ["Goleiro", "Zagueiro", "Lateral", "Volante", "Meio de campo", "Atacante"]
MAX_IMAGEM_BYTES = 3 * 1024 * 1024
# =========================================================


def conexao():
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL nao configurada. Conecte o banco Neon na aba Storage da Vercel."
        )
    return psycopg2.connect(url)


_tabela_ok = False


def garante_tabela():
    """Cria a tabela na primeira vez (idempotente)."""
    global _tabela_ok
    if _tabela_ok:
        return
    conn = conexao()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS figurinhas (
                    id        SERIAL PRIMARY KEY,
                    nome      TEXT NOT NULL,
                    turma     TEXT NOT NULL,
                    posicao   TEXT NOT NULL,
                    imagem    TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                )
                """
            )
        _tabela_ok = True
    finally:
        conn.close()


# ===================== TEMPLATES (HTML) =====================
TEMPLATES = {
    'base.html': r'''<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block titulo %}Copa de Figurinhas{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Sora:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root{
      --verde:#0a7d3c;
      --verde-fundo:#062d1b;
      --verde-fundo2:#04150f;
      --ouro:#f4c542;
      --ouro-escuro:#b8860b;
      --branco:#fdfdfb;
      --cinza:#9fb3a8;
      --erro:#ef4444;
      --pos-goleiro:#f59e0b;
      --pos-zagueiro:#2563eb;
      --pos-lateral:#06b6d4;
      --pos-volante:#8b5cf6;
      --pos-meio-de-campo:#16a34a;
      --pos-atacante:#dc2626;
    }
    *{margin:0;padding:0;box-sizing:border-box}
    body{
      font-family:'Sora',sans-serif;
      color:var(--branco);
      min-height:100vh;
      background:
        radial-gradient(1200px 600px at 50% -10%, rgba(244,197,66,.10), transparent 60%),
        radial-gradient(900px 500px at 90% 110%, rgba(10,125,60,.35), transparent 60%),
        linear-gradient(160deg, var(--verde-fundo) 0%, var(--verde-fundo2) 100%);
      background-attachment:fixed;
      position:relative;
      overflow-x:hidden;
    }
    /* linhas do campo decorativas */
    body::before{
      content:"";position:fixed;inset:0;pointer-events:none;opacity:.06;
      background-image:
        repeating-linear-gradient(0deg, transparent 0 78px, #fff 78px 80px);
    }
    .container{max-width:1180px;margin:0 auto;padding:24px 20px 60px;position:relative;z-index:1}

    /* Cabeçalho do site */
    .topo{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
      padding:16px 0 28px;border-bottom:1px solid rgba(244,197,66,.18);margin-bottom:34px}
    .marca{display:flex;align-items:center;gap:14px}
    .bola{width:46px;height:46px;border-radius:50%;background:
        radial-gradient(circle at 35% 30%, #fff 0 16%, transparent 17%),
        radial-gradient(circle at 70% 65%, #1a1a1a 0 12%, transparent 13%),
        radial-gradient(circle at 30% 75%, #1a1a1a 0 10%, transparent 11%),
        #f3f3f3;
      border:2px solid #111;box-shadow:0 6px 18px rgba(0,0,0,.45)}
    .marca h1{font-family:'Anton',sans-serif;font-size:1.5rem;letter-spacing:.5px;line-height:1;text-transform:uppercase}
    .marca h1 span{color:var(--ouro)}
    .marca small{display:block;color:var(--cinza);font-weight:500;font-size:.72rem;letter-spacing:2px;text-transform:uppercase;margin-top:3px}

    .btn{display:inline-flex;align-items:center;gap:8px;cursor:pointer;border:none;
      font-family:'Sora',sans-serif;font-weight:700;font-size:.92rem;border-radius:999px;
      padding:12px 22px;text-decoration:none;transition:transform .15s, box-shadow .15s, filter .15s}
    .btn:hover{transform:translateY(-2px)}
    .btn-ouro{background:linear-gradient(180deg,#ffd866,var(--ouro) 60%,var(--ouro-escuro));color:#3a2a00;
      box-shadow:0 8px 22px rgba(244,197,66,.35)}
    .btn-ouro:hover{filter:brightness(1.05);box-shadow:0 12px 28px rgba(244,197,66,.45)}
    .btn-verde{background:linear-gradient(180deg,#16a34a,#0a7d3c);color:#fff;box-shadow:0 8px 22px rgba(10,125,60,.4)}
    .btn-fantasma{background:rgba(255,255,255,.06);color:var(--branco);border:1px solid rgba(255,255,255,.18)}
    .btn-perigo{background:rgba(239,68,68,.12);color:#fecaca;border:1px solid rgba(239,68,68,.4);padding:8px 14px;font-size:.82rem}
    .btn-perigo:hover{background:rgba(239,68,68,.25)}

    .flash{padding:12px 18px;border-radius:12px;margin-bottom:14px;font-weight:600;font-size:.92rem}
    .flash.erro{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.5);color:#fecaca}
    .flash.ok{background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.5);color:#bbf7d0}

    .rodape{text-align:center;color:var(--cinza);font-size:.8rem;margin-top:48px;opacity:.7}

    {% block estilo %}{% endblock %}
  </style>
</head>
<body>
  <div class="container">
    <header class="topo">
      <a href="{{ url_for('index') }}" class="marca" style="text-decoration:none;color:inherit">
        <div class="bola"></div>
        <div>
          <h1>Copa de <span>Figurinhas</span></h1>
          <small>Álbum da turma 2026</small>
        </div>
      </a>
      {% block acao_topo %}
        <a href="{{ url_for('login') }}" class="btn btn-fantasma">🔒 Área do professor</a>
      {% endblock %}
    </header>

    {% with mensagens = get_flashed_messages(with_categories=true) %}
      {% for categoria, msg in mensagens %}
        <div class="flash {{ categoria }}">{{ msg }}</div>
      {% endfor %}
    {% endwith %}

    {% block conteudo %}{% endblock %}

    <p class="rodape">Atividade escolar • Copa de Figurinhas ⚽</p>
  </div>
  {% block scripts %}{% endblock %}
</body>
</html>
''',
    'index.html': r'''{% extends "base.html" %}
{% block titulo %}Crie sua figurinha{% endblock %}

{% block estilo %}
  .grade{display:grid;grid-template-columns:1.05fr .95fr;gap:42px;align-items:start}
  @media(max-width:860px){.grade{grid-template-columns:1fr;gap:32px}}

  .intro h2{font-family:'Anton',sans-serif;font-size:2.4rem;line-height:1.02;text-transform:uppercase;letter-spacing:.5px}
  .intro h2 b{color:var(--ouro)}
  .intro p{color:var(--cinza);margin-top:10px;max-width:46ch;line-height:1.5}

  .campo{margin-top:22px}
  .campo label{display:block;font-weight:700;font-size:.82rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--ouro);margin-bottom:9px}
  .campo input[type=text], .campo select{
    width:100%;padding:14px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.16);
    background:rgba(255,255,255,.05);color:#fff;font-family:'Sora',sans-serif;font-size:1rem;outline:none;transition:.15s}
  .campo input[type=text]:focus, .campo select:focus{border-color:var(--ouro);background:rgba(255,255,255,.09)}
  .campo select option{background:#0a2a1a;color:#fff}

  .posicoes{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  @media(max-width:520px){.posicoes{grid-template-columns:repeat(2,1fr)}}
  .pos-btn{position:relative;cursor:pointer}
  .pos-btn input{position:absolute;opacity:0;inset:0;cursor:pointer}
  .pos-btn span{display:flex;flex-direction:column;align-items:center;gap:4px;padding:12px 6px;border-radius:12px;
    border:1.5px solid rgba(255,255,255,.14);background:rgba(255,255,255,.04);font-weight:600;font-size:.86rem;transition:.15s}
  .pos-btn .ic{font-size:1.4rem}
  .pos-btn input:checked + span{border-color:var(--cor);background:color-mix(in srgb, var(--cor) 25%, transparent);box-shadow:0 0 0 1px var(--cor) inset}

  .foto-drop{margin-top:9px;border:2px dashed rgba(244,197,66,.4);border-radius:14px;padding:26px;text-align:center;
    cursor:pointer;transition:.15s;background:rgba(255,255,255,.03)}
  .foto-drop:hover{border-color:var(--ouro);background:rgba(244,197,66,.06)}
  .foto-drop .ic{font-size:2rem}
  .foto-drop p{color:var(--cinza);margin-top:6px;font-size:.9rem}
  .foto-drop b{color:var(--ouro)}
  #arquivo{display:none}

  .enviar{margin-top:26px;width:100%;justify-content:center;font-size:1.05rem;padding:16px}

  /* ===== FIGURINHA ===== */
  .preview-wrap{position:sticky;top:24px;display:flex;flex-direction:column;align-items:center;gap:14px}
  .dica{color:var(--cinza);font-size:.82rem;letter-spacing:1px;text-transform:uppercase}
  .figurinha{
    --cor:#888;
    width:300px;max-width:82vw;aspect-ratio:63/88;border-radius:18px;position:relative;overflow:hidden;
    background:linear-gradient(160deg,#10261b,#081912);
    padding:7px;
    box-shadow:0 24px 60px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.06) inset;
  }
  /* borda metálica */
  .figurinha::before{content:"";position:absolute;inset:0;border-radius:18px;padding:3px;
    background:linear-gradient(135deg, var(--cor), #fff6, var(--cor));
    -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
  .fig-inner{height:100%;border-radius:13px;overflow:hidden;display:flex;flex-direction:column;background:#06140d;position:relative}
  .fig-faixa{background:linear-gradient(180deg, var(--cor), color-mix(in srgb,var(--cor) 60%, #000));
    color:#fff;padding:9px 14px;display:flex;align-items:center;justify-content:space-between;
    font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:.84rem;text-shadow:0 1px 2px rgba(0,0,0,.4)}
  .fig-faixa .ic{font-size:1.1rem}
  .fig-foto{flex:1;position:relative;background:
      repeating-linear-gradient(45deg,#0c1f15 0 12px,#0a1b12 12px 24px);display:flex;align-items:center;justify-content:center}
  .fig-foto img{width:100%;height:100%;object-fit:cover;display:none}
  .fig-foto .placeholder{color:#3f5a4b;font-size:2.6rem}
  .fig-rodape{padding:11px 14px 13px;background:linear-gradient(0deg,#05110b,transparent);position:relative}
  .fig-rodape .nome{font-family:'Anton',sans-serif;font-size:1.35rem;text-transform:uppercase;line-height:1;letter-spacing:.5px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fig-rodape .meta{display:flex;justify-content:space-between;align-items:center;margin-top:6px}
  .fig-rodape .turma{color:var(--cinza);font-size:.78rem;font-weight:600}
  .fig-selo{font-family:'Anton',sans-serif;font-size:.72rem;letter-spacing:1px;color:var(--ouro);
    border:1px solid var(--ouro);padding:2px 8px;border-radius:6px}
  /* brilho holográfico */
  .fig-inner::after{content:"";position:absolute;inset:0;pointer-events:none;
    background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.14) 48%,transparent 60%);
    background-size:250% 250%;animation:brilho 5s linear infinite}
  @keyframes brilho{0%{background-position:140% 0}100%{background-position:-40% 0}}
{% endblock %}

{% block conteudo %}
<form action="{{ url_for('salvar') }}" method="POST" id="form" class="grade">
  <div>
    <div class="intro">
      <h2>Monte a sua <b>figurinha</b> da Copa ⚽</h2>
      <p>Coloque sua foto, escreva seu nome e escolha em que posição você joga. A figurinha vai pro álbum da turma!</p>
    </div>

    <div class="campo">
      <label for="nome">Seu nome</label>
      <input type="text" id="nome" name="nome" maxlength="40" placeholder="Ex.: Maria Silva" required>
    </div>

    <div class="campo">
      <label for="turma">Sua turma</label>
      <select id="turma" name="turma" required>
        <option value="" disabled selected>Selecione...</option>
        <option value="8º ano">8º ano</option>
        <option value="9º ano">9º ano</option>
        <option value="1º ano EM">1º ano (Ensino Médio)</option>
        <option value="2º ano EM">2º ano (Ensino Médio)</option>
        <option value="3º ano EM">3º ano (Ensino Médio)</option>
      </select>
    </div>

    <div class="campo">
      <label>Sua posição</label>
      <div class="posicoes">
        {% set icones = {'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥'} %}
        {% for p in posicoes %}
        <label class="pos-btn" style="--cor:var(--pos-{{ p|lower|replace(' ','-') }})">
          <input type="radio" name="posicao" value="{{ p }}" required>
          <span><span class="ic">{{ icones[p] }}</span>{{ p }}</span>
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="campo">
      <label>Sua foto</label>
      <label for="arquivo" class="foto-drop" id="drop">
        <div class="ic">📷</div>
        <p><b>Toque para escolher</b> ou tirar uma foto</p>
      </label>
      <input type="file" id="arquivo" accept="image/*" capture="user">
    </div>

    <input type="hidden" name="imagem" id="imagem">
    <button type="submit" class="btn btn-ouro enviar" id="btnEnviar">⭐ Salvar minha figurinha</button>
  </div>

  <!-- PRÉVIA -->
  <div class="preview-wrap">
    <span class="dica">Prévia ao vivo</span>
    <div class="figurinha" id="card">
      <div class="fig-inner">
        <div class="fig-faixa"><span id="fPos">Posição</span><span class="ic" id="fIcon">⚽</span></div>
        <div class="fig-foto">
          <img id="fImg" alt="">
          <span class="placeholder" id="fPlace">🧍</span>
        </div>
        <div class="fig-rodape">
          <div class="nome" id="fNome">SEU NOME</div>
          <div class="meta">
            <span class="turma" id="fTurma">Turma</span>
            <span class="fig-selo">COPA 26</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</form>
{% endblock %}

{% block scripts %}
<script>
  const cores = {
    'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4',
    'Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626'
  };
  const icones = {
    'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃',
    'Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥'
  };

  const card = document.getElementById('card');
  const nome = document.getElementById('nome');
  const turma = document.getElementById('turma');
  const arquivo = document.getElementById('arquivo');
  const imagemInput = document.getElementById('imagem');

  nome.addEventListener('input', () => {
    document.getElementById('fNome').textContent = nome.value.trim() ? nome.value.toUpperCase() : 'SEU NOME';
  });
  turma.addEventListener('change', () => {
    document.getElementById('fTurma').textContent = turma.value || 'Turma';
  });
  document.querySelectorAll('input[name=posicao]').forEach(r => {
    r.addEventListener('change', () => {
      card.style.setProperty('--cor', cores[r.value]);
      document.getElementById('fPos').textContent = r.value;
      document.getElementById('fIcon').textContent = icones[r.value];
    });
  });

  // Reduz a foto no navegador (máx 600px) e converte em base64
  arquivo.addEventListener('change', () => {
    const file = arquivo.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
      const img = new Image();
      img.onload = () => {
        const MAX = 600;
        let {width, height} = img;
        if (width > height && width > MAX){ height = height*MAX/width; width = MAX; }
        else if (height > MAX){ width = width*MAX/height; height = MAX; }
        const canvas = document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        canvas.getContext('2d').drawImage(img, 0, 0, width, height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.82);
        imagemInput.value = dataUrl;
        const fImg = document.getElementById('fImg');
        fImg.src = dataUrl; fImg.style.display = 'block';
        document.getElementById('fPlace').style.display = 'none';
        document.getElementById('drop').querySelector('p').innerHTML = '<b>Foto pronta!</b> Toque para trocar';
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });

  // Evita envio sem foto
  document.getElementById('form').addEventListener('submit', e => {
    if (!imagemInput.value){ e.preventDefault(); alert('Escolha uma foto antes de salvar!'); }
    else { document.getElementById('btnEnviar').textContent = 'Salvando...'; }
  });
</script>
{% endblock %}
''',
    'sucesso.html': r'''{% extends "base.html" %}
{% block titulo %}Figurinha salva!{% endblock %}
{% block estilo %}
  .ok-box{max-width:560px;margin:40px auto;text-align:center;
    background:rgba(255,255,255,.04);border:1px solid rgba(244,197,66,.25);border-radius:20px;padding:48px 32px}
  .ok-box .estrela{font-size:3.4rem}
  .ok-box h2{font-family:'Anton',sans-serif;font-size:2.2rem;text-transform:uppercase;margin-top:8px}
  .ok-box h2 b{color:var(--ouro)}
  .ok-box p{color:var(--cinza);margin:14px 0 28px;line-height:1.5}
{% endblock %}
{% block conteudo %}
<div class="ok-box">
  <div class="estrela">🌟</div>
  <h2>Boa, <b>{{ nome.split(' ')[0] }}</b>!</h2>
  <p>Sua figurinha entrou no álbum da turma. Quer fazer outra ou já era?</p>
  <a href="{{ url_for('index') }}" class="btn btn-ouro">➕ Criar outra figurinha</a>
</div>
{% endblock %}
''',
    'login.html': r'''{% extends "base.html" %}
{% block titulo %}Acesso do professor{% endblock %}
{% block acao_topo %}
  <a href="{{ url_for('index') }}" class="btn btn-fantasma">← Voltar</a>
{% endblock %}
{% block estilo %}
  .login-box{max-width:420px;margin:40px auto;background:rgba(255,255,255,.04);
    border:1px solid rgba(244,197,66,.22);border-radius:20px;padding:40px 32px;text-align:center}
  .login-box .ic{font-size:2.6rem}
  .login-box h2{font-family:'Anton',sans-serif;font-size:1.9rem;text-transform:uppercase;margin-top:6px}
  .login-box p{color:var(--cinza);margin:8px 0 24px;font-size:.92rem}
  .login-box input{width:100%;padding:14px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.16);
    background:rgba(255,255,255,.05);color:#fff;font-family:'Sora',sans-serif;font-size:1rem;text-align:center;letter-spacing:2px;outline:none}
  .login-box input:focus{border-color:var(--ouro)}
  .login-box button{width:100%;justify-content:center;margin-top:16px}
{% endblock %}
{% block conteudo %}
<div class="login-box">
  <div class="ic">🔒</div>
  <h2>Área do professor</h2>
  <p>Digite a senha para ver as figurinhas da turma.</p>
  <form method="POST">
    <input type="password" name="senha" placeholder="Senha" autofocus required>
    <button type="submit" class="btn btn-ouro">Entrar</button>
  </form>
</div>
{% endblock %}
''',
    'painel.html': r'''{% extends "base.html" %}
{% block titulo %}Painel do professor{% endblock %}
{% block acao_topo %}
  <a href="{{ url_for('sair') }}" class="btn btn-fantasma">Sair →</a>
{% endblock %}
{% block estilo %}
  .painel-topo{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:24px}
  .painel-topo h2{font-family:'Anton',sans-serif;font-size:2rem;text-transform:uppercase}
  .contador{color:var(--ouro);font-weight:700}
  .filtros{display:flex;gap:10px;flex-wrap:wrap}
  .filtros select{padding:11px 14px;border-radius:10px;border:1px solid rgba(255,255,255,.16);
    background:rgba(255,255,255,.05);color:#fff;font-family:'Sora',sans-serif;font-size:.9rem;outline:none}
  .filtros select option{background:#0a2a1a}

  .album{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px}
  .vazio{text-align:center;color:var(--cinza);padding:60px 20px;font-size:1.05rem}

  .figurinha{--cor:#888;width:100%;aspect-ratio:63/88;border-radius:14px;position:relative;overflow:hidden;
    background:linear-gradient(160deg,#10261b,#081912);padding:6px;
    box-shadow:0 14px 34px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.05) inset}
  .figurinha::before{content:"";position:absolute;inset:0;border-radius:14px;padding:2.5px;
    background:linear-gradient(135deg,var(--cor),#fff6,var(--cor));
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
  .fig-inner{height:100%;border-radius:10px;overflow:hidden;display:flex;flex-direction:column;background:#06140d}
  .fig-faixa{background:linear-gradient(180deg,var(--cor),color-mix(in srgb,var(--cor) 60%,#000));
    color:#fff;padding:6px 10px;display:flex;align-items:center;justify-content:space-between;
    font-weight:700;text-transform:uppercase;letter-spacing:.5px;font-size:.66rem}
  .fig-faixa .ic{font-size:.95rem}
  .fig-foto{flex:1}
  .fig-foto img{width:100%;height:100%;object-fit:cover;display:block}
  .fig-rodape{padding:8px 10px 10px;background:#05110b}
  .fig-rodape .nome{font-family:'Anton',sans-serif;font-size:.95rem;text-transform:uppercase;line-height:1;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fig-rodape .meta{display:flex;justify-content:space-between;align-items:center;margin-top:4px}
  .fig-rodape .turma{color:var(--cinza);font-size:.66rem;font-weight:600}
  .fig-selo{font-family:'Anton',sans-serif;font-size:.6rem;color:var(--ouro);border:1px solid var(--ouro);padding:1px 5px;border-radius:4px}

  .card-bloco{display:flex;flex-direction:column;gap:8px}
  .card-info{display:flex;justify-content:space-between;align-items:center}
  .card-info .data{color:var(--cinza);font-size:.7rem}
{% endblock %}
{% block conteudo %}
<div class="painel-topo">
  <div>
    <h2>Álbum da turma</h2>
    <span class="contador">{{ figurinhas|length }} figurinha(s){% if total != figurinhas|length %} de {{ total }} no total{% endif %}</span>
  </div>
  <form class="filtros" method="GET">
    <select name="turma" onchange="this.form.submit()">
      <option value="">Todas as turmas</option>
      {% for t in turmas %}
        <option value="{{ t }}" {% if t==turma_filtro %}selected{% endif %}>{{ t }}</option>
      {% endfor %}
    </select>
    <select name="posicao" onchange="this.form.submit()">
      <option value="">Todas as posições</option>
      {% for p in posicoes %}
        <option value="{{ p }}" {% if p==posicao_filtro %}selected{% endif %}>{{ p }}</option>
      {% endfor %}
    </select>
  </form>
</div>

{% if figurinhas %}
  {% set icones = {'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥'} %}
  <div class="album">
    {% for f in figurinhas %}
    <div class="card-bloco">
      <div class="figurinha" style="--cor:var(--pos-{{ f.posicao|lower|replace(' ','-') }})">
        <div class="fig-inner">
          <div class="fig-faixa"><span>{{ f.posicao }}</span><span class="ic">{{ icones[f.posicao] }}</span></div>
          <div class="fig-foto"><img src="{{ f.imagem }}" alt="{{ f.nome }}"></div>
          <div class="fig-rodape">
            <div class="nome">{{ f.nome|upper }}</div>
            <div class="meta"><span class="turma">{{ f.turma }}</span><span class="fig-selo">COPA 26</span></div>
          </div>
        </div>
      </div>
      <div class="card-info">
        <span class="data">{{ f.criado_em }}</span>
        <form method="POST" action="{{ url_for('excluir', fig_id=f.id) }}"
              onsubmit="return confirm('Remover a figurinha de {{ f.nome }}?')">
          <button type="submit" class="btn btn-perigo">Remover</button>
        </form>
      </div>
    </div>
    {% endfor %}
  </div>
{% else %}
  <div class="vazio">Nenhuma figurinha ainda. Quando os alunos enviarem, elas aparecem aqui. ⚽</div>
{% endif %}
{% endblock %}
''',
}

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # Vercel limita o corpo (~4.5MB)
app.jinja_loader = DictLoader(TEMPLATES)


def login_obrigatorio(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("professor"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ----------------------- ALUNO -----------------------
@app.route("/")
def index():
    return render_template("index.html", posicoes=POSICOES)


@app.route("/salvar", methods=["POST"])
def salvar():
    nome = (request.form.get("nome") or "").strip()
    turma = (request.form.get("turma") or "").strip()
    posicao = (request.form.get("posicao") or "").strip()
    imagem = request.form.get("imagem") or ""

    erros = []
    if len(nome) < 2:
        erros.append("Escreva seu nome.")
    if len(turma) < 1:
        erros.append("Selecione sua turma.")
    if posicao not in POSICOES:
        erros.append("Selecione uma posicao valida.")
    if not imagem.startswith("data:image/"):
        erros.append("Escolha uma foto.")
    if len(imagem) > MAX_IMAGEM_BYTES * 1.4:
        erros.append("A foto ficou muito grande, tente outra.")

    if erros:
        for e in erros:
            flash(e, "erro")
        return redirect(url_for("index"))

    garante_tabela()
    conn = conexao()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO figurinhas (nome, turma, posicao, imagem, criado_em) "
                "VALUES (%s, %s, %s, %s, %s)",
                (nome[:60], turma[:20], posicao, imagem,
                 datetime.now().strftime("%d/%m/%Y %H:%M")),
            )
    finally:
        conn.close()
    return render_template("sucesso.html", nome=nome)


# --------------------- PROFESSOR ---------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("senha") or "") == SENHA_PROFESSOR:
            session["professor"] = True
            return redirect(url_for("painel"))
        flash("Senha incorreta.", "erro")
    return render_template("login.html")


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("index"))


@app.route("/painel")
@login_obrigatorio
def painel():
    garante_tabela()
    turma_filtro = request.args.get("turma", "")
    posicao_filtro = request.args.get("posicao", "")

    sql = "SELECT id, nome, turma, posicao, imagem, criado_em FROM figurinhas WHERE TRUE"
    params = []
    if turma_filtro:
        sql += " AND turma = %s"
        params.append(turma_filtro)
    if posicao_filtro:
        sql += " AND posicao = %s"
        params.append(posicao_filtro)
    sql += " ORDER BY turma, nome"

    conn = conexao()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.execute("SELECT DISTINCT turma FROM figurinhas ORDER BY turma")
            turmas = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM figurinhas")
            total = cur.fetchone()[0]
    finally:
        conn.close()

    figurinhas = [
        {"id": r[0], "nome": r[1], "turma": r[2],
         "posicao": r[3], "imagem": r[4], "criado_em": r[5]}
        for r in rows
    ]
    return render_template(
        "painel.html", figurinhas=figurinhas, turmas=turmas,
        posicoes=POSICOES, turma_filtro=turma_filtro,
        posicao_filtro=posicao_filtro, total=total,
    )


@app.route("/excluir/<int:fig_id>", methods=["POST"])
@login_obrigatorio
def excluir(fig_id):
    conn = conexao()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM figurinhas WHERE id = %s", (fig_id,))
    finally:
        conn.close()
    flash("Figurinha removida.", "ok")
    return redirect(request.referrer or url_for("painel"))


# Permite testar localmente: python api/index.py
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
