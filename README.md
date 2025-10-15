# House Laundry Queue

Tired of roommates cutting the line for the washing machine? Not anymore!

A tiny **self-hosted web app** for coordinating shared laundry machines.
Run it once on a home server, and everyone on your Wi-Fi can queue, start, and track laundry cycles from their phone or laptop.

![index](images/index.png#pic_center)

![logs](images/logs.png#pic_center)
---

## ✨ Features

### 👥 Queue management

- Multiple machines (each with configurable capacity)
- Automatic **front-of-queue** logic and idle timers
- Cancel or delete unstarted jobs
- Remarks for quick notes

### ⏱ Cycle tracking

- Set **duration** (hours + minutes) when starting
- Live countdown timer:
  - **Running** → blue badge
  - **Awaiting pickup** → green badge
  - **Overdue** → red badge with negative timer
- Done button for early finish

🧰 Admin tools

- Add or remove machines (red ✖ delete button per card)
- **Operation logs**
- Clean, minimal UI with automatic time updates

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app binds to 0.0.0.0 by default, so any device on your local Wi-Fi can join the fun.
*(Bonus points if you add it to your home screen like a mobile app!)*

## 🌐 Deploy on Your LAN

### Option 1: Directly on a Home Server

```bash
python run.py
```

Find your LAN IP (e.g. 123.456.7.89) and access the app at `http://123.456.7.89:8000`.

### Option 2: Using Docker

```bash
# if you're first using this project, you may want build it first
docker compose up --build

docker compose up -d
```

Now open http://<server-ip>:8000 from any device on your Wi-Fi.

## 🧼 Etiquette (optional but recommended 😁)

1. Don’t start before your turn — the system knows!
2. Leave a note in **Remarks** if you’ll be late.
3. Press **Done** when finished — free the machine for others.
4. Be kind: shared laundry, shared peace ✌️

## 📜 License

MIT — free to use, modify, and share.
*(Leave a star if it saves your roommate relationships!)*
