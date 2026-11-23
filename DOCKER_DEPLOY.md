# Docker deployment

This Compose project is named `qms`. Its app, Redis, network, and static volume are separate from other Compose projects on the server. Only the Nginx container publishes a host port, 8099 by default. The app and Redis ports are private.

The Docker deployment keeps its own SQLite database and uploads under `~/QMS/docker-data/`. It does not write to the host deployment's `db.sqlite3` or `media/`.

Before pulling the commit that stops tracking `db.sqlite3`, stop only the old QMS process, then save its database outside the repository. Git may remove or refuse to overwrite a tracked database during this update. Do not run `git pull` on a live QMS database. The other server services can stay running.

On the server, from `~/QMS`, after these files have been pushed:

```bash
pgrep -af 'manage.py runserver'
# Stop only the identified QMS process, for example: kill QMS_PID
cp -p db.sqlite3 "$HOME/qms-db-before-docker.sqlite3"
git restore -- db.sqlite3
git pull
cp -p "$HOME/qms-db-before-docker.sqlite3" db.sqlite3
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
id -u
id -g
ss -ltnp | grep ':8099 ' || true
```

Edit `.env`: replace `QMS_SECRET_KEY` with the generated value, set `QMS_ALLOWED_HOSTS` to the server IP or domain, and set `QMS_UID` and `QMS_GID` to the outputs of `id -u` and `id -g`. Set `QMS_PORT` to another unused port if 8099 is occupied. Keep `.env` private.

If you already pulled the commit that removed `db.sqlite3`, first stop the old QMS process (identify it with `pgrep -af 'manage.py runserver'`; stop only those QMS PIDs). Restore the newest database backup you have to `db.sqlite3`. If there is no backup, the last database tracked by Git can be recovered with:

```bash
git show e62f5dd:db.sqlite3 > db.sqlite3
```

That Git copy contains only data present in that commit. Check it before relying on it if the server has had newer data.

Copy the current QMS data into the isolated Docker data directory:

```bash
mkdir -p docker-data/media
cp -p db.sqlite3 docker-data/db.sqlite3
cp -a media/. docker-data/media/
sudo chown -R "$(id -u):$(id -g)" docker-data
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app
curl -I http://127.0.0.1:8099/qms/
```

Open `http://SERVER_IP:8099/qms/`. Permit inbound TCP 8099 in the server or cloud firewall if remote clients cannot connect. Keep the old QMS process stopped after the switch. If it is started again for a comparison, its SQLite database and uploads will diverge from the Docker copy. Other services on the server are unaffected.

For later updates, run `git pull && docker compose up -d --build`. Migrations and static collection run at startup. To warm the audio cache, run `docker compose exec app python manage.py warm_audio_cache --tokens 10 --counters 10`. To stop only this stack, run `docker compose down` from `~/QMS`; this preserves the SQLite file, uploads, and static volume.

## If Nginx returns 502 and the app reports a SQLite error

The app must be able to write the database and its SQLite journal files in `docker-data/`. First update to the Compose version that mounts that directory at `/app/data`, then check the host files:

```bash
docker compose down
git pull
ls -ld docker-data docker-data/db.sqlite3
```

`docker-data/db.sqlite3` must be a regular file. If Docker created it as an empty directory because it was missing, remove only that empty directory with `rmdir docker-data/db.sqlite3`, then copy the newest QMS database backup into that path. If no newer backup exists, recover the Git snapshot with `git show e62f5dd:db.sqlite3 > docker-data/db.sqlite3`.

Then align ownership with the UID and GID in `.env` and restart QMS:

```bash
sudo chown -R "$(id -u):$(id -g)" docker-data
sed -i "s/^QMS_UID=.*/QMS_UID=$(id -u)/; s/^QMS_GID=.*/QMS_GID=$(id -g)/" .env
docker compose up -d --build
docker compose logs --tail=40 app
curl -I http://127.0.0.1:8099/qms/
```
