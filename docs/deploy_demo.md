# Deploying the web demo

The web demo (`app.py`) runs on **Streamlit Community Cloud**, which is free and runs straight from this GitHub repository. It uses the same code as `try_sentence.py`.

## Try it on your own computer first

```
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens the app at `http://localhost:8501`. Press Ctrl + C in the terminal to stop it.

## Deploy it (once, about 5 minutes)

1. Push `app.py` and the updated `requirements.txt` to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with the GitHub account that owns the repository.
3. Click **Create app** → **Deploy a public app from GitHub**.
4. Fill in:
   - Repository: `Adeleyi/hausa-rmbt`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: `hausa-rbmt` (gives `https://hausa-rbmt.streamlit.app`; if that name is taken, choose another and update the link in the README)
5. Click **Deploy**. The first start takes a few minutes while it installs the libraries.

After that, every `git push` updates the app automatically.

## Before a presentation

- Free apps go to sleep when nobody has used them for a while. **Open the link about 10 minutes before you present** and click "Yes, get this app back up" if you see it.
- Keep screenshots in the slides in case the Wi-Fi fails.
- Practise with sentences you know work, for example (all from the development set):
  - English → Hausa: *The boy laughed.* · *Ada is a teacher.* · *The children are in the house.* · *Musa gave Ada a book.* · *When the rain started, the children ran inside.*
  - Hausa → English: *Musa bai halarci taron ba.* · *Ada tana da mota.* · *Me Musa ya saya?* · *Mutumin da ya kira jiya kawuna ne.*
- Greetings and idioms (*Ina kwana?*) are not translated correctly yet: the system reads them word by word.