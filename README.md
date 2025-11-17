# 💸 MoneyMate – Chatbot Financeiro com LLaMA 3.3 (Groq) + Flask + Supabase

**MoneyMate** é um chatbot financeiro inteligente que interpreta mensagens em linguagem natural, extrai valores e categoriza automaticamente cada gasto usando o modelo **LLaMA 3.3 70B** da **Groq API**.

O sistema roda localmente usando **Flask** e possui uma interface web simples em **HTML/CSS/JS**, além de armazenar todos os registros no **Supabase**.

---

## 🚀 Funcionalidades

- Interpretação de texto natural (ex: “Uber 25 reais”, “Comprei um lanche por 22,90”)
- Extração automática de valor e descrição
- Classificação inteligente da categoria do gasto usando IA (Groq LLaMA 3.3-70B)
- Registro persistido no Supabase
- Interface web própria para testes
- API HTTP em Flask
- Separação clara entre backend, frontend e banco

---

## 🧠 Inteligência Artificial (Groq)

O chatbot utiliza o modelo: LLaMA 3.3-70B (Meta)

## 🧰 Tecnologias Utilizadas

| Camada      | Tecnologia |
|-------------|------------|
| Backend     | Flask (Python) |
| IA          | Groq API (LLaMA 3.3 70B) |
| Banco       | Supabase (PostgreSQL + API) |
| Frontend    | HTML, CSS, JavaScript |
| Integração  | Fetch API (frontend → Flask) |

---

## 📁 Estrutura do Projeto

```plaintext
MONEY-MATE/
│
├── app/
│   ├── moneymate_web.py       # (principal)
│   ├── supabase_client.py     # Conexão e operações no Supabase
│
├── templates/
│   └── index.html             # Interface web
│
├── static/
│   ├── style.css
│   └── script.js
│
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
