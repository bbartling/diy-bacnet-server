### 🐳 1. Install Docker & docker-compose on Raspberry Pi


* Modify the JSON file in the root directory for identifying your BACnet server device to an external control system trying to discover it. The Docker process copies this over when app boots. 

```json
{
  "device_name": "BensBACnetServer",
  "device_instance": 1234567
}
```

**Note** - The commands below were tested on an older raspberry pi 3 model which used legacy docker compose with commands that have dashes such as a `docker-compose up --build -d`. Newer Pis or versions of docker compose you need to run commands without the dash such as a `docker compose up --build -d`.

```bash
# Install Docker
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Then **log out and back in**, or run:
```bash
newgrp docker
```

To install docker-compose plugin:
```bash
sudo apt install docker-compose-plugin
```

Verify:
```bash
docker-compose version
```

---

### ⚙️ 2. Build & Run Using docker-compose

From the project root where `docker-compose.yml` is located:

```bash
docker compose up --build -d
```

---

### 📋 3. View Logs

All services:
```bash
docker compose logs -f
```

Just BACnet server:
```bash
docker compose logs -f bacnet_server
```

---

### 🧹 4. Stop and Clean Up
* note: `-d` stands for detached mode, which means “Run the containers in the background.”

```bash
docker compose build && docker-compose up -d --remove-orphans
```
---

### 🔁 5. Rebuild Completely (Clean Start)
* note: `-d` stands for detached mode, which means “Run the containers in the background.”
```bash
docker compose build --no-cache && docker-compose up -d --remove-orphans
```

---

## 🔄 Common Docker Commands

### List all containers:
```bash
docker ps -a
```

### Stop and remove all containers:
```bash
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
```

### Full cleanup (⚠️ removes everything):
```bash
docker system prune -a --volumes
```

---

## ✅ Troubleshooting

### Access Docker shell:
```bash
docker exec -it bacnet_server bash
```

### Test BACnet communication from other free 3rd party tools:
Use `bacnet-read` or `bacnet-write` from tools like Yabe or the BACnet Discovery Tool (BDT)
