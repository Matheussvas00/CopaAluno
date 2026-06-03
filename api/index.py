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

# Posicoes de jogadores (livres para o aluno) e de comissao (exigem senha)
POSICOES_JOGADORES = ["Goleiro", "Zagueiro", "Lateral", "Volante", "Meio de campo", "Atacante"]
POSICOES_COMISSAO = ["Técnico", "Auxiliar", "Árbitra"]
POSICOES = POSICOES_JOGADORES + POSICOES_COMISSAO

# Turmas disponiveis. "Todas as turmas" e so para a comissao (ex.: a diretora/arbitra).
TURMAS = ["9º A", "9º B", "9º C", "1º D", "1º E", "2º D", "2º E", "2º F", "3º B", "3º C"]
TURMA_COMISSAO = "Todas as turmas"

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
  <title>{% block titulo %}Copa CESANAM{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Sora:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root{
      --ouro:#f4c542;
      --ouro-escuro:#b8860b;
      --branco:#fdfdfb;
      --cinza:#c3d6c9;
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
      position:relative;
      overflow-x:hidden;
      background:
        linear-gradient(160deg, rgba(4,30,16,.74) 0%, rgba(3,20,12,.82) 100%),
        repeating-linear-gradient(90deg,#2f7d3a 0 64px,#2a7236 64px 128px);
      background-attachment:fixed;
    }
    /* marcações do campo (linha central + círculo central), bem sutis */
    body::before{
      content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
      background:
        radial-gradient(circle at 50% 50%, transparent 86px, rgba(255,255,255,.12) 88px, rgba(255,255,255,.12) 91px, transparent 93px) no-repeat 50% 50%,
        linear-gradient(rgba(255,255,255,.10),rgba(255,255,255,.10)) no-repeat 50% 50% / 100% 2px;
    }
    .container{max-width:1180px;margin:0 auto;padding:24px 20px 60px;position:relative;z-index:1}

    /* Cabeçalho */
    .topo{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
      padding:14px 0 26px;border-bottom:1px solid rgba(244,197,66,.22);margin-bottom:32px}
    .marca{display:flex;align-items:center;gap:16px;text-decoration:none;color:inherit;min-width:0}
    .logo-badge{flex:none;width:62px;height:62px;border-radius:14px;background:#fff;
      display:flex;align-items:center;justify-content:center;padding:6px;
      box-shadow:0 6px 18px rgba(0,0,0,.45)}
    .logo-badge img{width:100%;height:100%;object-fit:contain}
    .marca .txt{min-width:0}
    .marca h1{font-family:'Anton',sans-serif;font-size:clamp(1.05rem,2.3vw,1.6rem);line-height:1.05;
      letter-spacing:.5px;text-transform:uppercase;color:var(--ouro);text-shadow:0 2px 6px rgba(0,0,0,.5)}
    .marca h1 b{color:var(--branco);font-weight:400}
    .marca small{display:block;color:var(--cinza);font-weight:600;font-size:.72rem;letter-spacing:1.5px;
      text-transform:uppercase;margin-top:4px;text-shadow:0 1px 3px rgba(0,0,0,.5)}

    .btn{display:inline-flex;align-items:center;gap:8px;cursor:pointer;border:none;
      font-family:'Sora',sans-serif;font-weight:700;font-size:.92rem;border-radius:999px;
      padding:12px 22px;text-decoration:none;transition:transform .15s, box-shadow .15s, filter .15s;white-space:nowrap}
    .btn:hover{transform:translateY(-2px)}
    .btn-ouro{background:linear-gradient(180deg,#ffd866,var(--ouro) 60%,var(--ouro-escuro));color:#3a2a00;
      box-shadow:0 8px 22px rgba(244,197,66,.35)}
    .btn-ouro:hover{filter:brightness(1.05);box-shadow:0 12px 28px rgba(244,197,66,.45)}
    .btn-verde{background:linear-gradient(180deg,#16a34a,#0a7d3c);color:#fff;box-shadow:0 8px 22px rgba(10,125,60,.4)}
    .btn-fantasma{background:rgba(0,0,0,.35);color:var(--branco);border:1px solid rgba(255,255,255,.22)}
    .btn-perigo{background:rgba(239,68,68,.16);color:#fecaca;border:1px solid rgba(239,68,68,.45);padding:8px 14px;font-size:.82rem}
    .btn-perigo:hover{background:rgba(239,68,68,.28)}

    .flash{padding:12px 18px;border-radius:12px;margin-bottom:14px;font-weight:600;font-size:.92rem}
    .flash.erro{background:rgba(239,68,68,.18);border:1px solid rgba(239,68,68,.55);color:#fecaca}
    .flash.ok{background:rgba(34,197,94,.18);border:1px solid rgba(34,197,94,.55);color:#bbf7d0}

    .rodape{text-align:center;color:var(--cinza);font-size:.8rem;margin-top:48px;opacity:.8;text-shadow:0 1px 3px rgba(0,0,0,.5)}

    {% block estilo %}{% endblock %}
  </style>
</head>
<body>
  <div class="container">
    <header class="topo">
      <a href="{{ url_for('index') }}" class="marca">
        <div class="logo-badge"><img src="data:image/png;base64,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" alt="CESANAM"></div>
        <div class="txt">
          <h1><b>COPA</b> CESANAM — Colégio Estadual Ana Nastre de Melo</h1>
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
  @media(max-width:860px){.grade{grid-template-columns:1fr;gap:28px}}

  .intro h2{font-family:'Anton',sans-serif;font-size:clamp(1.7rem,5vw,2.4rem);line-height:1.02;text-transform:uppercase;letter-spacing:.5px;text-shadow:0 2px 6px rgba(0,0,0,.5)}
  .intro h2 b{color:var(--ouro)}
  .intro p{color:var(--cinza);margin-top:10px;max-width:46ch;line-height:1.5;text-shadow:0 1px 3px rgba(0,0,0,.5)}

  .campo{margin-top:22px}
  .campo > label{display:block;font-weight:700;font-size:.82rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--ouro);margin-bottom:9px;text-shadow:0 1px 3px rgba(0,0,0,.5)}
  .campo input[type=text], .campo input[type=password], .campo select{
    width:100%;padding:14px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.2);
    background:rgba(0,0,0,.35);color:#fff;font-family:'Sora',sans-serif;font-size:1rem;outline:none;transition:.15s}
  .campo input:focus, .campo select:focus{border-color:var(--ouro);background:rgba(0,0,0,.5)}
  .campo select option{background:#0a2a1a;color:#fff}

  .grupo-pos{font-weight:700;font-size:.74rem;letter-spacing:1.5px;text-transform:uppercase;color:#cfe3d6;margin:14px 0 8px;opacity:.85}
  .posicoes{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  @media(max-width:520px){.posicoes{grid-template-columns:repeat(2,1fr)}}
  .pos-btn{position:relative;cursor:pointer}
  .pos-btn input{position:absolute;opacity:0;inset:0;cursor:pointer}
  .pos-btn span{display:flex;flex-direction:column;align-items:center;gap:4px;padding:12px 6px;border-radius:12px;
    border:1.5px solid rgba(255,255,255,.16);background:rgba(0,0,0,.3);font-weight:600;font-size:.86rem;transition:.15s;text-align:center}
  .pos-btn .ic{font-size:1.4rem}
  .pos-btn input:checked + span{border-color:var(--cor);background:color-mix(in srgb, var(--cor) 32%, rgba(0,0,0,.4));box-shadow:0 0 0 1px var(--cor) inset}

  #campoSenha{display:none}
  #campoSenha.show{display:block}
  .aviso-staff{font-size:.82rem;color:#ffd866;background:rgba(244,197,66,.1);border:1px solid rgba(244,197,66,.35);
    border-radius:10px;padding:10px 12px;margin-top:8px;line-height:1.4}

  .foto-drop{margin-top:9px;border:2px dashed rgba(244,197,66,.45);border-radius:14px;padding:26px;text-align:center;
    cursor:pointer;transition:.15s;background:rgba(0,0,0,.25)}
  .foto-drop:hover{border-color:var(--ouro);background:rgba(244,197,66,.08)}
  .foto-drop .ic{font-size:2rem}
  .foto-drop p{color:var(--cinza);margin-top:6px;font-size:.9rem}
  .foto-drop b{color:var(--ouro)}
  #arquivo{display:none}

  .enviar{margin-top:26px;width:100%;justify-content:center;font-size:1.05rem;padding:16px}

  /* ===== FIGURINHA (prévia) ===== */
  .preview-wrap{position:sticky;top:24px;display:flex;flex-direction:column;align-items:center;gap:14px}
  @media(max-width:860px){.preview-wrap{position:static;order:-1}}
  .dica{color:var(--cinza);font-size:.82rem;letter-spacing:1px;text-transform:uppercase;text-shadow:0 1px 3px rgba(0,0,0,.5)}
  .figurinha{--cor:#888;width:300px;max-width:82vw;aspect-ratio:63/88;border-radius:18px;position:relative;overflow:hidden;
    background:linear-gradient(160deg,#10261b,#081912);padding:7px;
    box-shadow:0 24px 60px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.06) inset}
  .figurinha::before{content:"";position:absolute;inset:0;border-radius:18px;padding:3px;
    background:linear-gradient(135deg, var(--cor), #fff6, var(--cor));
    -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
  .fig-inner{height:100%;border-radius:13px;overflow:hidden;display:flex;flex-direction:column;background:#06140d;position:relative}
  .fig-faixa{flex-shrink:0;background:linear-gradient(180deg, var(--cor), color-mix(in srgb,var(--cor) 60%, #000));
    color:#fff;padding:9px 14px;display:flex;align-items:center;justify-content:space-between;
    font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:.84rem;text-shadow:0 1px 2px rgba(0,0,0,.4)}
  .fig-faixa .ic{font-size:1.1rem}
  .fig-foto{flex:1 1 auto;min-height:0;overflow:hidden;position:relative;display:flex;align-items:center;justify-content:center;
    background:repeating-linear-gradient(45deg,#0c1f15 0 12px,#0a1b12 12px 24px)}
  .fig-foto img{width:100%;height:100%;object-fit:contain;display:none}
  .fig-foto .placeholder{color:#3f5a4b;font-size:2.6rem}
  .fig-rodape{flex-shrink:0;padding:11px 14px 13px;background:linear-gradient(0deg,#05110b,transparent);position:relative}
  .fig-rodape .nome{font-family:'Anton',sans-serif;font-size:1.35rem;text-transform:uppercase;line-height:1;letter-spacing:.5px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fig-rodape .meta{display:flex;justify-content:space-between;align-items:center;margin-top:6px}
  .fig-rodape .turma{color:var(--cinza);font-size:.78rem;font-weight:600}
  .fig-selo{font-family:'Anton',sans-serif;font-size:.72rem;letter-spacing:1px;color:var(--ouro);
    border:1px solid var(--ouro);padding:2px 8px;border-radius:6px}
  .fig-inner::after{content:"";position:absolute;inset:0;pointer-events:none;
    background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.14) 48%,transparent 60%);
    background-size:250% 250%;animation:brilho 5s linear infinite}
  @keyframes brilho{0%{background-position:140% 0}100%{background-position:-40% 0}}
{% endblock %}

{% block conteudo %}
{% set cores = {'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'} %}
{% set icones = {'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'} %}
<form action="{{ url_for('salvar') }}" method="POST" id="form" class="grade">
  <div>
    <div class="intro">
      <h2>Monte a sua <b>figurinha</b> da Copa ⚽</h2>
      <p>Coloque sua foto, escreva seu nome e escolha em que posição você joga. A figurinha vai pro álbum da turma!</p>
    </div>

    <div class="campo">
      <label for="nome">Nome</label>
      <input type="text" id="nome" name="nome" maxlength="50" placeholder="Ex.: Maria Silva" required>
    </div>

    <div class="campo">
      <label for="turma">Turma</label>
      <select id="turma" name="turma" required>
        <option value="" disabled selected>Selecione...</option>
        {% for t in turmas %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
      </select>
    </div>

    <div class="campo">
      <label>Posição</label>
      <div class="grupo-pos">⚽ Jogadores</div>
      <div class="posicoes">
        {% for p in jogadores %}
        <label class="pos-btn" style="--cor:{{ cores[p] }}">
          <input type="radio" name="posicao" value="{{ p }}" data-staff="0" required>
          <span><span class="ic">{{ icones[p] }}</span>{{ p }}</span>
        </label>
        {% endfor %}
      </div>
      <div class="grupo-pos">🔒 Comissão técnica (precisa da senha do professor)</div>
      <div class="posicoes">
        {% for p in comissao %}
        <label class="pos-btn" style="--cor:{{ cores[p] }}">
          <input type="radio" name="posicao" value="{{ p }}" data-staff="1">
          <span><span class="ic">{{ icones[p] }}</span>{{ p }}</span>
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="campo" id="campoSenha">
      <label for="senha_staff">Senha do professor</label>
      <input type="password" id="senha_staff" name="senha_staff" placeholder="Digite a senha para cadastrar a comissão">
      <div class="aviso-staff">As posições de Técnico, Auxiliar e Árbitra são protegidas por senha do professor.</div>
    </div>

    <div class="campo">
      <label>Foto</label>
      <label for="arquivo" class="foto-drop" id="drop">
        <div class="ic">📷</div>
        <p><b>Toque para escolher</b> ou tirar uma foto</p>
      </label>
      <input type="file" id="arquivo" accept="image/*">
    </div>

    <input type="hidden" name="imagem" id="imagem">
    <button type="submit" class="btn btn-ouro enviar" id="btnEnviar">⭐ Salvar figurinha</button>
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
  var cores={'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'};
  var icones={'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'};

  var card=document.getElementById('card');
  var nome=document.getElementById('nome');
  var turma=document.getElementById('turma');
  var arquivo=document.getElementById('arquivo');
  var imagemInput=document.getElementById('imagem');
  var campoSenha=document.getElementById('campoSenha');

  nome.addEventListener('input',function(){
    document.getElementById('fNome').textContent = nome.value.trim()? nome.value.toUpperCase() : 'SEU NOME';
  });
  turma.addEventListener('change',function(){
    document.getElementById('fTurma').textContent = turma.value || 'Turma';
  });
  var radios=document.querySelectorAll('input[name=posicao]');
  for(var i=0;i<radios.length;i++){
    radios[i].addEventListener('change',function(){
      card.style.setProperty('--cor', cores[this.value]||'#888');
      document.getElementById('fPos').textContent=this.value;
      document.getElementById('fIcon').textContent=icones[this.value]||'⚽';
      // mostra/esconde senha conforme comissão
      if(this.dataset.staff==='1'){ campoSenha.classList.add('show'); }
      else { campoSenha.classList.remove('show'); document.getElementById('senha_staff').value=''; }
    });
  }

  arquivo.addEventListener('change',function(){
    var file=arquivo.files[0]; if(!file) return;
    var reader=new FileReader();
    reader.onload=function(e){
      var img=new Image();
      img.onload=function(){
        var MAX=600, w=img.width, h=img.height;
        if(w>h && w>MAX){ h=h*MAX/w; w=MAX; } else if(h>MAX){ w=w*MAX/h; h=MAX; }
        var canvas=document.createElement('canvas'); canvas.width=w; canvas.height=h;
        canvas.getContext('2d').drawImage(img,0,0,w,h);
        var dataUrl=canvas.toDataURL('image/jpeg',0.82);
        imagemInput.value=dataUrl;
        var fImg=document.getElementById('fImg');
        fImg.src=dataUrl; fImg.style.display='block';
        document.getElementById('fPlace').style.display='none';
        document.getElementById('drop').querySelector('p').innerHTML='<b>Foto pronta!</b> Toque para trocar';
      };
      img.src=e.target.result;
    };
    reader.readAsDataURL(file);
  });

  document.getElementById('form').addEventListener('submit',function(e){
    if(!imagemInput.value){ e.preventDefault(); alert('Escolha uma foto antes de salvar!'); return; }
    document.getElementById('btnEnviar').textContent='Salvando...';
  });
</script>
{% endblock %}
''',
    'sucesso.html': r'''{% extends "base.html" %}
{% block titulo %}Figurinha salva!{% endblock %}
{% block estilo %}
  .ok-wrap{max-width:480px;margin:32px auto;text-align:center}
  .ok-topo{background:rgba(255,255,255,.04);border:1px solid rgba(244,197,66,.25);border-radius:20px;padding:32px 32px 24px}
  .ok-topo .estrela{font-size:3rem}
  .ok-topo h2{font-family:'Anton',sans-serif;font-size:2rem;text-transform:uppercase;margin-top:6px}
  .ok-topo h2 b{color:var(--ouro)}
  .ok-topo p{color:var(--cinza);margin:10px 0 0;line-height:1.5;font-size:.93rem}
  .fig-preview{margin:20px auto 0;display:flex;justify-content:center}
  .acoes-ok{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:20px}
  .figurinha{--cor:#888;width:240px;aspect-ratio:63/88;border-radius:16px;position:relative;overflow:hidden;
    background:linear-gradient(160deg,#10261b,#081912);padding:6px;
    box-shadow:0 20px 50px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.06) inset}
  .figurinha::before{content:"";position:absolute;inset:0;border-radius:16px;padding:2.5px;
    background:linear-gradient(135deg,var(--cor),#fff6,var(--cor));
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
  .fig-inner{height:100%;border-radius:11px;overflow:hidden;display:flex;flex-direction:column;background:#06140d;position:relative}
  .fig-faixa{flex-shrink:0;background:linear-gradient(180deg,var(--cor),color-mix(in srgb,var(--cor) 60%,#000));
    color:#fff;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;
    font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:.8rem}
  .fig-faixa .ic{font-size:1rem}
  .fig-foto{flex:1 1 auto;min-height:0;overflow:hidden;display:flex;align-items:center;justify-content:center;
    background:repeating-linear-gradient(45deg,#0c1f15 0 12px,#0a1b12 12px 24px)}
  .fig-foto img{width:100%;height:100%;object-fit:contain}
  .fig-rodape{flex-shrink:0;padding:9px 12px 11px;background:linear-gradient(0deg,#05110b,transparent)}
  .fig-rodape .nome{font-family:'Anton',sans-serif;font-size:1.15rem;text-transform:uppercase;line-height:1;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fig-rodape .meta{display:flex;justify-content:space-between;align-items:center;margin-top:5px}
  .fig-rodape .turma{color:var(--cinza);font-size:.72rem;font-weight:600}
  .fig-selo{font-family:'Anton',sans-serif;font-size:.65rem;color:var(--ouro);border:1px solid var(--ouro);padding:2px 6px;border-radius:5px}
  .fig-inner::after{content:"";position:absolute;inset:0;pointer-events:none;
    background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.14) 48%,transparent 60%);
    background-size:250% 250%;animation:brilho 5s linear infinite}
  @keyframes brilho{0%{background-position:140% 0}100%{background-position:-40% 0}}
{% endblock %}
{% block conteudo %}
{% set cores = {'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'} %}
{% set icones = {'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'} %}
<div class="ok-wrap">
  <div class="ok-topo">
    <div class="estrela">🌟</div>
    <h2>Boa, <b>{{ nome.split(' ')[0] }}</b>!</h2>
    <p>Sua figurinha entrou no álbum da turma!</p>
  </div>

  <div class="fig-preview">
    <div class="figurinha" style="--cor:{{ cores.get(posicao,'#888') }}">
      <div class="fig-inner">
        <div class="fig-faixa"><span>{{ posicao }}</span><span class="ic">{{ icones.get(posicao,'⚽') }}</span></div>
        <div class="fig-foto"><img id="fImg" src="{{ imagem }}" alt="{{ nome }}"></div>
        <div class="fig-rodape">
          <div class="nome">{{ nome|upper }}</div>
          <div class="meta"><span class="turma">{{ turma }}</span><span class="fig-selo">COPA 26</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="acoes-ok">
    <button class="btn btn-ouro" id="btnDl" onclick="baixarFigurinha()">⬇️ Baixar minha figurinha</button>
    <a href="{{ url_for('index') }}" class="btn btn-fantasma">➕ Criar outra</a>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script>
  var _dados={nome:{{ nome|tojson }},turma:{{ turma|tojson }},posicao:{{ posicao|tojson }}};
  var CORES={'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'};
  var ICONES={'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'};
  function hexRgb(h){h=h.replace('#','');return[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];}
  function mistura(a,b,t){var A=hexRgb(a),B=hexRgb(b);return 'rgb('+A.map(function(v,i){return Math.round(v+(B[i]-v)*t);}).join(',')+')';}
  function rrect(ctx,x,y,w,h,r){if(ctx.roundRect){ctx.beginPath();ctx.roundRect(x,y,w,h,r);return;}ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
  function fitFont(ctx,text,fam,maxW,start,min){var px=start;ctx.font=px+'px '+fam;while(ctx.measureText(text).width>maxW&&px>min){px-=2;ctx.font=px+'px '+fam;}return px;}
  function contain(ctx,img,x,y,w,h){var ar=img.width/img.height,tr=w/h,dw,dh;if(ar>tr){dw=w;dh=w/ar;}else{dh=h;dw=h*ar;}ctx.drawImage(img,0,0,img.width,img.height,x+(w-dw)/2,y+(h-dh)/2,dw,dh);}
  function desenharCartao(ctx,x,y,w,h,d,img){
    var cor=CORES[d.posicao]||'#888';
    var r=w*0.06,pad=w*0.028,ir=r*0.7;
    rrect(ctx,x,y,w,h,r);
    var g=ctx.createLinearGradient(x,y,x+w,y+h);g.addColorStop(0,'#10261b');g.addColorStop(1,'#06140d');ctx.fillStyle=g;ctx.fill();
    var bw=w*0.02,bg=ctx.createLinearGradient(x,y,x+w,y+h);bg.addColorStop(0,cor);bg.addColorStop(.5,'#ffffff');bg.addColorStop(1,cor);
    ctx.lineWidth=bw;ctx.strokeStyle=bg;rrect(ctx,x+bw/2,y+bw/2,w-bw,h-bw,r);ctx.stroke();
    var ix=x+pad,iy=y+pad,iw=w-2*pad,ih=h-2*pad;
    ctx.save();rrect(ctx,ix,iy,iw,ih,ir);ctx.clip();ctx.fillStyle='#06140d';ctx.fillRect(ix,iy,iw,ih);
    var bandH=ih*0.092,b3=ctx.createLinearGradient(0,iy,0,iy+bandH);b3.addColorStop(0,cor);b3.addColorStop(1,mistura(cor,'#000000',.45));
    ctx.fillStyle=b3;ctx.fillRect(ix,iy,iw,bandH);
    ctx.fillStyle='#fff';ctx.textBaseline='middle';ctx.textAlign='left';
    var fp=fitFont(ctx,d.posicao.toUpperCase(),'Anton',iw*0.72,bandH*0.55,9);
    ctx.font=fp+'px Anton';ctx.fillText(d.posicao.toUpperCase(),ix+iw*0.05,iy+bandH*0.55);
    ctx.textAlign='right';ctx.font=(bandH*0.55)+'px Sora';ctx.fillText(ICONES[d.posicao]||'⚽',ix+iw*0.95,iy+bandH*0.52);
    var fy=iy+bandH,fH=ih*0.69,fgr=ctx.createLinearGradient(0,fy,0,fy+fH);fgr.addColorStop(0,'#0c1f15');fgr.addColorStop(1,'#0a1b12');
    ctx.fillStyle=fgr;ctx.fillRect(ix,fy,iw,fH);
    if(img){ctx.save();ctx.beginPath();ctx.rect(ix,fy,iw,fH);ctx.clip();contain(ctx,img,ix,fy,iw,fH);ctx.restore();}
    var ry=fy+fH,rH=ih-(bandH+fH),gr=ctx.createLinearGradient(0,ry,0,ry+rH);gr.addColorStop(0,'rgba(5,17,11,.15)');gr.addColorStop(.45,'#05110b');gr.addColorStop(1,'#05110b');
    ctx.fillStyle=gr;ctx.fillRect(ix,ry,iw,rH);
    ctx.textBaseline='alphabetic';ctx.textAlign='left';ctx.fillStyle='#fff';
    var np=fitFont(ctx,d.nome.toUpperCase(),'Anton',iw*0.9,rH*0.40,9);
    ctx.font=np+'px Anton';ctx.fillText(d.nome.toUpperCase(),ix+iw*0.05,ry+rH*0.48);
    ctx.font=(rH*0.17)+'px Sora';ctx.fillStyle='#c3d6c9';ctx.fillText(d.turma,ix+iw*0.05,ry+rH*0.80);
    var slo='COPA 26',sw2=ctx.measureText(slo).width,padx=iw*0.035,sh=rH*0.27,sx=ix+iw*0.95-sw2-2*padx,sy=ry+rH*0.60;
    ctx.lineWidth=Math.max(1,w*0.004);ctx.strokeStyle='#f4c542';rrect(ctx,sx,sy,sw2+2*padx,sh,sh*0.3);ctx.stroke();
    ctx.fillStyle='#f4c542';ctx.textBaseline='middle';ctx.fillText(slo,sx+padx,sy+sh*0.55);
    ctx.restore();
  }
  async function baixarFigurinha(){
    var btn=document.getElementById('btnDl');btn.disabled=true;btn.textContent='Gerando...';
    try{
      await document.fonts.ready;
      var fImg=document.getElementById('fImg');
      var img=await new Promise(function(res,rej){var i=new Image();i.onload=function(){res(i);};i.onerror=rej;i.crossOrigin='anonymous';i.src=fImg.src;});
      var scale=2.4,W=440,H=Math.round(W*88/63);
      var cv=document.createElement('canvas');cv.width=W*scale;cv.height=H*scale;
      var ctx=cv.getContext('2d');ctx.scale(scale,scale);
      desenharCartao(ctx,3,3,W-6,H-6,_dados,img);
      cv.toBlob(function(blob){
        var a=document.createElement('a');a.href=URL.createObjectURL(blob);
        a.download='Figurinha_'+(_dados.nome||'').replace(/[^a-zA-Z0-9]/g,'_')+'.png';
        document.body.appendChild(a);a.click();a.remove();
        setTimeout(function(){URL.revokeObjectURL(a.href);},1500);
      },'image/png');
    }finally{setTimeout(function(){btn.disabled=false;btn.textContent='⬇️ Baixar minha figurinha';},500);}
  }
</script>
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
  .painel-topo{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:20px}
  .painel-topo h2{font-family:'Anton',sans-serif;font-size:2rem;text-transform:uppercase;text-shadow:0 2px 6px rgba(0,0,0,.5)}
  .contador{color:var(--ouro);font-weight:700}
  .barra{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:26px}
  .filtros{display:flex;gap:10px;flex-wrap:wrap}
  .filtros select{padding:11px 14px;border-radius:10px;border:1px solid rgba(255,255,255,.2);
    background:rgba(0,0,0,.35);color:#fff;font-family:'Sora',sans-serif;font-size:.9rem;outline:none}
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
  .fig-faixa{flex-shrink:0;background:linear-gradient(180deg,var(--cor),color-mix(in srgb,var(--cor) 60%,#000));
    color:#fff;padding:6px 10px;display:flex;align-items:center;justify-content:space-between;
    font-weight:700;text-transform:uppercase;letter-spacing:.5px;font-size:.66rem}
  .fig-faixa .ic{font-size:.95rem}
  .fig-foto{flex:1 1 auto;min-height:0;overflow:hidden;display:flex;align-items:center;justify-content:center;
    background:repeating-linear-gradient(45deg,#0c1f15 0 12px,#0a1b12 12px 24px)}
  .fig-foto img{width:100%;height:100%;object-fit:contain;display:block}
  .fig-rodape{flex-shrink:0;padding:8px 10px 10px;background:#05110b}
  .fig-rodape .nome{font-family:'Anton',sans-serif;font-size:.95rem;text-transform:uppercase;line-height:1;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fig-rodape .meta{display:flex;justify-content:space-between;align-items:center;margin-top:4px}
  .fig-rodape .turma{color:var(--cinza);font-size:.66rem;font-weight:600}
  .fig-selo{font-family:'Anton',sans-serif;font-size:.6rem;color:var(--ouro);border:1px solid var(--ouro);padding:1px 5px;border-radius:4px}

  .card-bloco{display:flex;flex-direction:column;gap:8px}
  .card-info{display:flex;justify-content:space-between;align-items:center;gap:8px}
  .card-info .data{color:var(--cinza);font-size:.7rem;text-shadow:0 1px 2px rgba(0,0,0,.5)}
  .acoes{display:flex;gap:6px}
  .btn-mini{cursor:pointer;border:1px solid rgba(244,197,66,.5);background:rgba(244,197,66,.14);color:#f4c542;
    font-family:'Sora',sans-serif;font-weight:700;font-size:.78rem;border-radius:8px;padding:7px 10px;white-space:nowrap}
  .btn-mini:hover{background:rgba(244,197,66,.28)}
  .btn-mini:disabled{opacity:.6;cursor:default}

  .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:9999;overflow-y:auto;
    padding:24px 16px;justify-content:center;align-items:flex-start}
  .modal-overlay.aberto{display:flex}
  .modal-box{background:#06281a;border:1px solid rgba(244,197,66,.3);border-radius:18px;padding:24px;
    width:100%;max-width:960px;margin:auto}
  .modal-topo{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
  .modal-topo h3{font-family:'Anton',sans-serif;font-size:1.5rem;color:var(--ouro);text-transform:uppercase}
  .modal-img{width:100%;border-radius:10px;display:block;max-height:80vh;object-fit:contain}
  .modal-acoes{display:flex;gap:12px;justify-content:center;margin-top:16px;flex-wrap:wrap}
{% endblock %}
{% block conteudo %}
<div class="painel-topo">
  <div>
    <h2>Álbum da turma</h2>
    <span class="contador">{{ figurinhas|length }} figurinha(s){% if total != figurinhas|length %} de {{ total }} no total{% endif %}</span>
  </div>
</div>

<div class="barra">
  <form class="filtros" method="GET">
    <select id="filtroTurma" name="turma" onchange="this.form.submit()">
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
  {% if figurinhas %}
  <button id="btnTime" class="btn btn-ouro" onclick="baixarTime()">⬇️ Baixar time da turma</button>
  <button id="btnPreview" class="btn btn-fantasma" onclick="visualizarTime()">👁️ Pré-visualizar</button>
  {% endif %}
</div>

<!-- Modal de pré-visualização -->
<div id="previewModal" class="modal-overlay">
  <div class="modal-box">
    <div class="modal-topo">
      <h3>Pré-visualização do time</h3>
      <button class="btn btn-fantasma" onclick="fecharPreview()" style="padding:8px 16px">✕ Fechar</button>
    </div>
    <img id="previewImg" class="modal-img" src="" alt="Prévia do time">
    <div class="modal-acoes">
      <button class="btn btn-ouro" onclick="_baixarPreview()">⬇️ Baixar imagem</button>
      <button class="btn btn-fantasma" onclick="fecharPreview()">✕ Fechar</button>
    </div>
  </div>
</div>

{% if figurinhas %}
  {% set icones = {'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'} %}
  {% set cores = {'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'} %}
  <div class="album">
    {% for f in figurinhas %}
    <div class="card-bloco" data-id="{{ f.id }}" data-nome="{{ f.nome }}" data-turma="{{ f.turma }}" data-posicao="{{ f.posicao }}">
      <div class="figurinha" style="--cor:{{ cores[f.posicao] }}">
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
        <div class="acoes">
          <button type="button" class="btn-mini" onclick="baixarUma(this)">⬇️ Baixar</button>
          <form method="POST" action="{{ url_for('excluir', fig_id=f.id) }}"
                onsubmit="return confirm('Remover a figurinha de {{ f.nome }}?')">
            <button type="submit" class="btn-perigo">Remover</button>
          </form>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
{% else %}
  <div class="vazio">Nenhuma figurinha ainda. Quando os alunos enviarem, elas aparecem aqui. ⚽</div>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
  var CORES={'Goleiro':'#f59e0b','Zagueiro':'#2563eb','Lateral':'#06b6d4','Volante':'#8b5cf6','Meio de campo':'#16a34a','Atacante':'#dc2626','Técnico':'#475569','Auxiliar':'#0d9488','Árbitra':'#d4a017'};
  var ICONES={'Goleiro':'🧤','Zagueiro':'🛡️','Lateral':'🏃','Volante':'⚙️','Meio de campo':'🎯','Atacante':'🔥','Técnico':'📋','Auxiliar':'📣','Árbitra':'🟨'};

  function carregarImagem(src){return new Promise(function(res,rej){var i=new Image();i.onload=function(){res(i);};i.onerror=rej;i.src=src;});}
  function baixarBlob(blob,nome){var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=nome;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);}
  function slug(s){return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9]+/g,'_').replace(/^_|_$/g,'')||'sem_nome';}
  function hexRgb(h){h=h.replace('#','');return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];}
  function mistura(a,b,t){var A=hexRgb(a),B=hexRgb(b);return 'rgb('+A.map(function(v,i){return Math.round(v+(B[i]-v)*t);}).join(',')+')';}

  function rrect(ctx,x,y,w,h,r){
    if(ctx.roundRect){ctx.beginPath();ctx.roundRect(x,y,w,h,r);return;}
    ctx.beginPath();ctx.moveTo(x+r,y);
    ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);
    ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
  }
  function cover(ctx,img,x,y,w,h){
    var ar=img.width/img.height, tr=w/h, sw,sh,sx,sy;
    if(ar>tr){sh=img.height;sw=sh*tr;sx=(img.width-sw)/2;sy=0;}
    else{sw=img.width;sh=sw/tr;sx=0;sy=(img.height-sh)/2;}
    ctx.drawImage(img,sx,sy,sw,sh,x,y,w,h);
  }
  function contain(ctx,img,x,y,w,h){
    var ar=img.width/img.height, tr=w/h, dw,dh;
    if(ar>tr){dw=w;dh=w/ar;}else{dh=h;dw=h*ar;}
    var dx=x+(w-dw)/2, dy=y+(h-dh)/2;
    ctx.drawImage(img,0,0,img.width,img.height,dx,dy,dw,dh);
  }
  function fitFont(ctx,text,fam,maxW,start,min){
    var px=start;ctx.font=px+'px '+fam;
    while(ctx.measureText(text).width>maxW && px>min){px-=2;ctx.font=px+'px '+fam;}
    return px;
  }

  // Desenha uma figurinha completa em (x,y) tamanho w x h
  function desenharCartao(ctx,x,y,w,h,d,img){
    var cor=CORES[d.posicao]||'#888';
    var r=w*0.06, pad=w*0.028, ir=r*0.7;
    rrect(ctx,x,y,w,h,r);
    var g=ctx.createLinearGradient(x,y,x+w,y+h);g.addColorStop(0,'#10261b');g.addColorStop(1,'#06140d');
    ctx.fillStyle=g;ctx.fill();
    var bw=w*0.02;
    var bg=ctx.createLinearGradient(x,y,x+w,y+h);bg.addColorStop(0,cor);bg.addColorStop(.5,'#ffffff');bg.addColorStop(1,cor);
    ctx.lineWidth=bw;ctx.strokeStyle=bg;rrect(ctx,x+bw/2,y+bw/2,w-bw,h-bw,r);ctx.stroke();
    var ix=x+pad,iy=y+pad,iw=w-2*pad,ih=h-2*pad;
    ctx.save();rrect(ctx,ix,iy,iw,ih,ir);ctx.clip();
    ctx.fillStyle='#06140d';ctx.fillRect(ix,iy,iw,ih);
    // faixa
    var bandH=ih*0.092;
    var b3=ctx.createLinearGradient(0,iy,0,iy+bandH);b3.addColorStop(0,cor);b3.addColorStop(1,mistura(cor,'#000000',.45));
    ctx.fillStyle=b3;ctx.fillRect(ix,iy,iw,bandH);
    ctx.fillStyle='#fff';ctx.textBaseline='middle';ctx.textAlign='left';
    var fp=fitFont(ctx,d.posicao.toUpperCase(),'Anton',iw*0.72,bandH*0.55,9);
    ctx.font=fp+'px Anton';ctx.fillText(d.posicao.toUpperCase(),ix+iw*0.05,iy+bandH*0.55);
    ctx.textAlign='right';ctx.font=(bandH*0.55)+'px Sora';
    ctx.fillText(ICONES[d.posicao]||'⚽',ix+iw*0.95,iy+bandH*0.52);
    // foto
    var fy=iy+bandH, fH=ih*0.69;
    var fgr=ctx.createLinearGradient(0,fy,0,fy+fH);fgr.addColorStop(0,'#0c1f15');fgr.addColorStop(1,'#0a1b12');
    ctx.fillStyle=fgr;ctx.fillRect(ix,fy,iw,fH);
    if(img){ctx.save();ctx.beginPath();ctx.rect(ix,fy,iw,fH);ctx.clip();contain(ctx,img,ix,fy,iw,fH);ctx.restore();}
    // rodapé
    var ry=fy+fH, rH=ih-(bandH+fH);
    var gr=ctx.createLinearGradient(0,ry,0,ry+rH);gr.addColorStop(0,'rgba(5,17,11,.15)');gr.addColorStop(.45,'#05110b');gr.addColorStop(1,'#05110b');
    ctx.fillStyle=gr;ctx.fillRect(ix,ry,iw,rH);
    ctx.textBaseline='alphabetic';ctx.textAlign='left';ctx.fillStyle='#fff';
    var np=fitFont(ctx,d.nome.toUpperCase(),'Anton',iw*0.9,rH*0.40,9);
    ctx.font=np+'px Anton';ctx.fillText(d.nome.toUpperCase(),ix+iw*0.05,ry+rH*0.48);
    ctx.font=(rH*0.17)+'px Sora';ctx.fillStyle='#c3d6c9';
    ctx.fillText(d.turma,ix+iw*0.05,ry+rH*0.80);
    // selo
    ctx.font=(rH*0.17)+'px Anton';var selo='COPA 26';var sw=ctx.measureText(selo).width;
    var padx=iw*0.035, sh=rH*0.27, sx=ix+iw*0.95-sw-2*padx, sy=ry+rH*0.60;
    ctx.lineWidth=Math.max(1,w*0.004);ctx.strokeStyle='#f4c542';rrect(ctx,sx,sy,sw+2*padx,sh,sh*0.3);ctx.stroke();
    ctx.fillStyle='#f4c542';ctx.textBaseline='middle';ctx.fillText(selo,sx+padx,sy+sh*0.55);
    ctx.restore();
  }

  function desenharCampo(ctx,x,y,w,h){
    var faixa=h/16;
    for(var i=0;i<16;i++){ctx.fillStyle=(i%2?'#2a7236':'#2f7d3a');ctx.fillRect(x,y+i*faixa,w,faixa);}
    ctx.strokeStyle='rgba(255,255,255,.65)';ctx.lineWidth=Math.max(2,w*0.0035);
    var m=w*0.035;
    ctx.strokeRect(x+m,y+m,w-2*m,h-2*m);
    ctx.beginPath();ctx.moveTo(x+m,y+h/2);ctx.lineTo(x+w-m,y+h/2);ctx.stroke();
    ctx.beginPath();ctx.arc(x+w/2,y+h/2,w*0.11,0,Math.PI*2);ctx.stroke();
    ctx.beginPath();ctx.arc(x+w/2,y+h/2,w*0.008,0,Math.PI*2);ctx.fillStyle='rgba(255,255,255,.65)';ctx.fill();
    var aw=w*0.42, ah=h*0.12;
    ctx.strokeRect(x+(w-aw)/2,y+m,aw,ah);
    ctx.strokeRect(x+(w-aw)/2,y+h-m-ah,aw,ah);
  }

  async function baixarUma(btn){
    var b=btn.closest('.card-bloco');
    var d={nome:b.dataset.nome,turma:b.dataset.turma,posicao:b.dataset.posicao};
    var t=btn.textContent;btn.disabled=true;btn.textContent='Gerando...';
    try{
      await document.fonts.ready;
      var img=await carregarImagem(b.querySelector('.fig-foto img').src).catch(function(){return null;});
      var scale=2.4, W=440, H=Math.round(W*88/63);
      var cv=document.createElement('canvas');cv.width=W*scale;cv.height=H*scale;
      var ctx=cv.getContext('2d');ctx.scale(scale,scale);
      desenharCartao(ctx,3,3,W-6,H-6,d,img);
      cv.toBlob(function(blob){baixarBlob(blob,'Figurinha_'+slug(d.nome)+'_'+slug(d.turma)+'.png');},'image/png');
    }finally{setTimeout(function(){btn.disabled=false;btn.textContent=t;},500);}
  }

  // ── Geração do canvas do time (compartilhada entre download e pré-visualização) ──
  async function _gerarCanvas(){
    var blocos=[].slice.call(document.querySelectorAll('.card-bloco'));
    if(!blocos.length){alert('Não há figurinhas para gerar o time.');return null;}
    await document.fonts.ready;
    var dados=await Promise.all(blocos.map(async function(b){
      var img=await carregarImagem(b.querySelector('.fig-foto img').src).catch(function(){return null;});
      return {nome:b.dataset.nome,turma:b.dataset.turma,posicao:b.dataset.posicao,img:img};
    }));
    var sel=document.getElementById('filtroTurma');
    var turmaLabel=(sel&&sel.value)?sel.value:'';
    if(!turmaLabel){var ts=dados.map(function(d){return d.turma;}).filter(function(v,i,a){return a.indexOf(v)===i;});turmaLabel=ts.length===1?ts[0]:'Seleção da escola';}

    var comPos=['Técnico','Auxiliar','Árbitra'];
    var comissao=dados.filter(function(d){return comPos.indexOf(d.posicao)>=0;});
    var jogadores=dados.filter(function(d){return comPos.indexOf(d.posicao)<0;});

    // Mantém todos os 4 slots táticos (com arrays vazios) para posicionamento correto no campo
    var allGrupos=[
      jogadores.filter(function(d){return d.posicao==='Atacante';}),
      jogadores.filter(function(d){return d.posicao==='Volante'||d.posicao==='Meio de campo';}),
      jogadores.filter(function(d){return d.posicao==='Zagueiro'||d.posicao==='Lateral';}),
      jogadores.filter(function(d){return d.posicao==='Goleiro';})
    ];
    // Centro de cada zona como fração da altura do campo (ataque=topo, goleiro=fundo)
    var FRAC=[0.13,0.38,0.63,0.87];

    var FW=1800, gap=10, rowGap=22, sideM=40;
    var MAX_PER_ROW=11;

    function chunkN(arr,n){var o=[];for(var i=0;i<arr.length;i+=n)o.push(arr.slice(i,i+n));return o;}

    // Tamanho normal das figurinhas, só encolhe se a linha mais cheia não couber
    var maxGrupo=Math.max.apply(null,[1].concat(allGrupos.map(function(g){return Math.min(g.length,MAX_PER_ROW);})));
    var PREF_CARD_W=200,MIN_CARD_W=100,availW=FW-2*sideM;
    var cardW=(PREF_CARD_W*maxGrupo+gap*(maxGrupo-1)<=availW)?PREF_CARD_W:Math.max(MIN_CARD_W,Math.floor((availW-gap*(maxGrupo-1))/maxGrupo));
    var cardH=Math.round(cardW*88/63);

    // Comissão técnica: tamanho fixo, seção própria acima do campo
    var maxComRow=Math.min(comissao.length||1,6);
    var comCardW=Math.min(200,Math.max(140,Math.floor((FW-2*sideM-gap*(maxComRow-1))/maxComRow)));
    var comCardH=Math.round(comCardW*88/63);
    var COM_LABEL=50;
    var comRows=comissao.length?chunkN(comissao,maxComRow):[];
    var comSecH=comissao.length?(COM_LABEL+comRows.length*(comCardH+rowGap)+rowGap):0;

    // Altura do campo: mínimo proporcional ao campo real, expande se os grupos precisarem
    var MIN_FIELD_H=Math.round(FW*0.62); // ~1116px — aspecto ~1.61:1, próximo ao campo real
    var fieldH=MIN_FIELD_H;
    allGrupos.forEach(function(g,gi){
      if(!g.length)return;
      var nRows=Math.ceil(g.length/MAX_PER_ROW);
      var groupH=nRows*cardH+(nRows-1)*rowGap;
      var frac=FRAC[gi];
      // O grupo fica centralizado em frac*fieldH; garante que não saia pelo topo nem pelo fundo
      var needed=Math.ceil(Math.max(
        frac>0.01?(groupH/2+rowGap*2)/frac:0,
        (groupH/2+rowGap*2)/Math.max(0.01,1-frac)
      ));
      fieldH=Math.max(fieldH,needed);
    });

    var HH=180;
    var H=HH+comSecH+fieldH+30;
    var scale=1.6;
    var cv=document.createElement('canvas');cv.width=Math.round(FW*scale);cv.height=Math.round(H*scale);
    var ctx=cv.getContext('2d');ctx.scale(scale,scale);

    var fieldTop=HH+comSecH;
    desenharCampo(ctx,0,fieldTop,FW,fieldH+30);

    // Header
    ctx.fillStyle='#06281a';ctx.fillRect(0,0,FW,HH);
    ctx.fillStyle='#f4c542';ctx.fillRect(0,HH-5,FW,5);
    var logoEl=document.querySelector('.logo-badge img');var lx=50;
    if(logoEl){var lg=await carregarImagem(logoEl.src).catch(function(){return null;});
      if(lg){var bs=HH*0.62,bx=50,by=(HH-bs)/2,ipd=bs*0.1;
        ctx.fillStyle='#fff';rrect(ctx,bx,by,bs,bs,bs*0.16);ctx.fill();
        var ar=lg.width/lg.height,dw=bs-2*ipd,dh=dw/ar;if(dh>bs-2*ipd){dh=bs-2*ipd;dw=dh*ar;}
        ctx.drawImage(lg,bx+(bs-dw)/2,by+(bs-dh)/2,dw,dh);lx=bx+bs+28;}
    }
    ctx.textBaseline='middle';ctx.textAlign='left';
    ctx.fillStyle='#fff';ctx.font='36px Anton';ctx.fillText('TIME DA TURMA',lx,HH*0.36);
    ctx.fillStyle='#f4c542';ctx.font='54px Anton';ctx.fillText(turmaLabel.toUpperCase(),lx,HH*0.66);
    ctx.fillStyle='#c3d6c9';ctx.textAlign='right';ctx.font='22px Sora';
    ctx.fillText(jogadores.length+' jogadores • Copa CESANAM',FW-50,HH*0.32);
    ctx.fillText('Colégio Estadual Ana Nastre de Melo',FW-50,HH*0.64);

    // Seção comissão técnica (fundo distinto, fixada acima do campo)
    if(comissao.length){
      ctx.fillStyle='rgba(6,22,14,.96)';ctx.fillRect(0,HH,FW,comSecH);
      ctx.fillStyle='rgba(244,197,66,.18)';ctx.fillRect(0,HH,FW,COM_LABEL);
      ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#ffd866';ctx.font='28px Anton';
      ctx.fillText('— COMISSÃO TÉCNICA —',FW/2,HH+COM_LABEL/2);
      var cy=HH+COM_LABEL+rowGap;
      comRows.forEach(function(row){
        var tw=row.length*comCardW+(row.length-1)*gap,cx=(FW-tw)/2;
        row.forEach(function(d,k){desenharCartao(ctx,cx+k*(comCardW+gap),cy,comCardW,comCardH,d,d.img);});
        cy+=comCardH+rowGap;
      });
    }

    // Jogadores nas zonas táticas: cada grupo centralizado na sua fração do campo
    allGrupos.forEach(function(g,gi){
      if(!g.length)return;
      var rows=chunkN(g,MAX_PER_ROW);
      var groupH=rows.length*cardH+(rows.length-1)*rowGap;
      var centerY=fieldTop+FRAC[gi]*fieldH;
      var startY=Math.round(centerY-groupH/2);
      rows.forEach(function(row,ri){
        var n=row.length,tw=n*cardW+(n-1)*gap,sx=(FW-tw)/2;
        row.forEach(function(d,k){desenharCartao(ctx,sx+k*(cardW+gap),startY+ri*(cardH+rowGap),cardW,cardH,d,d.img);});
      });
    });

    return {cv:cv,label:turmaLabel};
  }

  // ── Download direto ──
  async function baixarTime(){
    var btn=document.getElementById('btnTime');var t=btn.textContent;
    btn.disabled=true;btn.textContent='Gerando...';
    try{
      var res=await _gerarCanvas();
      if(!res)return;
      res.cv.toBlob(function(blob){baixarBlob(blob,'Time_'+slug(res.label)+'.png');},'image/png');
    }catch(e){alert('Não consegui gerar a imagem do time: '+e);}
    finally{setTimeout(function(){btn.disabled=false;btn.textContent=t;},600);}
  }

  // ── Pré-visualização ──
  var _previewBlob=null,_previewLabel='';
  async function visualizarTime(){
    var btn=document.getElementById('btnPreview');var t=btn.textContent;
    btn.disabled=true;btn.textContent='Gerando...';
    try{
      var res=await _gerarCanvas();
      if(!res)return;
      res.cv.toBlob(function(blob){
        _previewBlob=blob;_previewLabel=res.label;
        var url=URL.createObjectURL(blob);
        var img=document.getElementById('previewImg');
        img.src=url;
        document.getElementById('previewModal').classList.add('aberto');
      },'image/png');
    }catch(e){alert('Não consegui gerar a prévia: '+e);}
    finally{setTimeout(function(){btn.disabled=false;btn.textContent=t;},600);}
  }
  function fecharPreview(){
    var img=document.getElementById('previewImg');
    if(img.src.startsWith('blob:'))URL.revokeObjectURL(img.src);
    img.src='';
    _previewBlob=null;
    document.getElementById('previewModal').classList.remove('aberto');
  }
  function _baixarPreview(){
    if(_previewBlob)baixarBlob(_previewBlob,'Time_'+slug(_previewLabel)+'.png');
  }

</script>
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
    return render_template("index.html",
                           jogadores=POSICOES_JOGADORES,
                           comissao=POSICOES_COMISSAO,
                           turmas=TURMAS,
                           turma_comissao=TURMA_COMISSAO)


@app.route("/salvar", methods=["POST"])
def salvar():
    nome = (request.form.get("nome") or "").strip()
    turma = (request.form.get("turma") or "").strip()
    posicao = (request.form.get("posicao") or "").strip()
    imagem = request.form.get("imagem") or ""
    senha_staff = request.form.get("senha_staff") or ""

    turmas_validas = TURMAS + [TURMA_COMISSAO]
    eh_comissao = posicao in POSICOES_COMISSAO

    erros = []
    if len(nome) < 2:
        erros.append("Escreva o nome.")
    if turma not in turmas_validas:
        erros.append("Selecione uma turma válida.")
    if posicao not in POSICOES:
        erros.append("Selecione uma posição válida.")
    if not imagem.startswith("data:image/"):
        erros.append("Escolha uma foto.")
    if len(imagem) > MAX_IMAGEM_BYTES * 1.4:
        erros.append("A foto ficou muito grande, tente outra.")

    # Regras da comissão técnica
    if eh_comissao:
        if senha_staff != SENHA_PROFESSOR:
            erros.append("As posições da comissão técnica (Técnico, Auxiliar, Árbitra) exigem a senha do professor.")
    else:
        if turma == TURMA_COMISSAO:
            erros.append("A opção \"Todas as turmas\" é só para a comissão técnica.")

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
                (nome[:60], turma[:30], posicao, imagem,
                 datetime.now().strftime("%d/%m/%Y %H:%M")),
            )
    finally:
        conn.close()
    return render_template("sucesso.html", nome=nome, turma=turma, posicao=posicao, imagem=imagem)


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
    if turma_filtro and turma_filtro != TURMA_COMISSAO:
        # Mostra a turma escolhida + a comissão geral (ex.: a diretora/árbitra de todos os times)
        sql += " AND (turma = %s OR (turma = %s AND posicao IN ('Técnico','Auxiliar','Árbitra')))"
        params.append(turma_filtro)
        params.append(TURMA_COMISSAO)
    elif turma_filtro:
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
