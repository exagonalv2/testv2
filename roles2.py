import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sys
import time
import traceback
import logging
import random
import aiohttp
from datetime import datetime, timezone
from collections import defaultdict
import functools

# ─────────────────────────────────────────────────────────────
#  🔴 INTERFAZ ROJA — Consola de inicio
# ─────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    R  = colorama.Fore.RED
    BR = colorama.Fore.LIGHTRED_EX
    W  = colorama.Fore.WHITE
    BW = colorama.Style.BRIGHT + colorama.Fore.WHITE
    RS = colorama.Style.RESET_ALL
    YL = colorama.Fore.YELLOW
    GR = colorama.Fore.LIGHTBLACK_EX
    DM = colorama.Style.DIM
except ImportError:
    R = BR = W = BW = RS = YL = GR = DM = ""

_BANNER = r"""
{r}╔══════════════════════════════════════════════════════════════╗
{r}║                                                              ║
{b}║   ███████╗██╗  ██╗ █████╗  ██████╗  ██████╗ ███╗   ██╗     ║
{b}║   ██╔════╝╚██╗██╔╝██╔══██╗██╔════╝ ██╔═══██╗████╗  ██║     ║
{r}║   █████╗   ╚███╔╝ ███████║██║  ███╗██║   ██║██╔██╗ ██║     ║
{b}║   ██╔══╝   ██╔██╗ ██╔══██║██║   ██║██║   ██║██║╚████║     ║
{r}║   ███████╗██╔╝╚██╗██║  ██║╚██████╔╝╚██████╔╝██║ ╚███║     ║
{b}║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚══╝     ║
{r}║                                                              ║
{r}║           [ by Exagonal  ·  AntiNuke v2.0 ]                 ║
{r}╚══════════════════════════════════════════════════════════════╝
""".format(r=R, b=BR)

def mostrar_banner(bot_user=None, guild_count=0):
    print(_BANNER)
    sep = f"{R}{'═' * 64}{RS}"
    print(sep)
    if bot_user:
        tag = f"{bot_user.name}#{bot_user.discriminator}" if bot_user.discriminator != "0" else bot_user.name
        print(f"  {BW}Bot     {RS}: {BR}{tag}{RS}  {GR}(ID: {bot_user.id}){RS}")
    print(f"  {BW}Prefijo {RS}: {BR}!comando{RS}  {GR}·{RS}  {BR}/comando{RS}")
    print(f"  {BW}Servers {RS}: {BR}{guild_count}{RS} servidor(es)")
    print(f"  {BW}Módulos {RS}: {BR}AntiNuke · Mod · Juegos · Anime · Fun · Roleplay{RS}")
    print(f"  {BW}Status  {RS}: {R}●{RS} {BR}Online{RS}")
    print(sep)
    print(f"  {YL}✔ Prefix commands ( ! ) listos{RS}")
    print(f"  {YL}✔ Slash commands  ( / ) sincronizados{RS}")
    print(sep)
    print()

# ─────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s » %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
log = logging.getLogger("bot")

# ═══════════════════════════════════════════════════════════════
#  MARCA DE AGUA — "by Exagonal" blindada en 3 capas
#
#  CAPA 1 → discord.Embed.to_dict()
#           Se ejecuta justo antes de serializar el embed para
#           enviarlo a la API. Es el último punto posible, por
#           lo que ningún código posterior puede quitarla.
#
#  CAPA 2 → discord.Embed.set_footer()
#           Si alguien llama a set_footer() explícitamente,
#           la marca se reinyecta de todas formas.
#
#  CAPA 3 → discord.abc.Messageable.send()
#           Revisión previa al envío como respaldo adicional.
#
#  Las referencias originales se guardan con nombres ofuscados
#  para dificultar que otro código las restaure.
# ═══════════════════════════════════════════════════════════════

_MARCA = "by Exagonal"

def _forzar_marca(embed: discord.Embed) -> None:
    """Inyecta la marca en el footer del embed si no está presente."""
    footer = embed.footer
    if not footer or not footer.text:
        # Llamada directa al método original guardado para evitar recursión
        _Embed_set_footer_orig(embed, text=_MARCA)
    elif _MARCA not in footer.text:
        nuevo = footer.text + f" | {_MARCA}"
        if footer.icon_url:
            _Embed_set_footer_orig(embed, text=nuevo, icon_url=footer.icon_url)
        else:
            _Embed_set_footer_orig(embed, text=nuevo)


# ── CAPA 2: patch de set_footer ──────────────────────────────
_Embed_set_footer_orig = discord.Embed.set_footer

def _Embed_set_footer_patched(self, *, text=discord.utils.MISSING, icon_url=discord.utils.MISSING):
    # Llama al original primero
    result = _Embed_set_footer_orig(self, text=text, icon_url=icon_url)
    # Luego garantiza que la marca esté presente
    footer = self.footer
    if footer and footer.text and _MARCA not in footer.text:
        _Embed_set_footer_orig(
            self,
            text=footer.text + f" | {_MARCA}",
            icon_url=footer.icon_url if footer.icon_url else discord.utils.MISSING
        )
    elif not footer or not footer.text:
        _Embed_set_footer_orig(self, text=_MARCA)
    return result

discord.Embed.set_footer = _Embed_set_footer_patched


# ── CAPA 1: patch de to_dict (última línea de defensa) ───────
_Embed_to_dict_orig = discord.Embed.to_dict

def _Embed_to_dict_patched(self):
    # Fuerza la marca usando el método original (sin recursión)
    footer = self.footer
    if not footer or not footer.text:
        _Embed_set_footer_orig(self, text=_MARCA)
    elif _MARCA not in footer.text:
        nuevo = footer.text + f" | {_MARCA}"
        if footer.icon_url:
            _Embed_set_footer_orig(self, text=nuevo, icon_url=footer.icon_url)
        else:
            _Embed_set_footer_orig(self, text=nuevo)
    return _Embed_to_dict_orig(self)

discord.Embed.to_dict = _Embed_to_dict_patched


# ── CAPA 3: patch de send (respaldo) ─────────────────────────
_Messageable_send_orig = discord.abc.Messageable.send

@functools.wraps(_Messageable_send_orig)
async def _Messageable_send_patched(self, content=None, **kwargs):
    embed = kwargs.get("embed")
    if embed is not None:
        _forzar_marca(embed)
    # Aplica también a listas de embeds (embeds=[...])
    for emb in kwargs.get("embeds") or []:
        _forzar_marca(emb)
    return await _Messageable_send_orig(self, content=content, **kwargs)

discord.abc.Messageable.send = _Messageable_send_patched

# ─────────────────────────────────────────────────────────────
#  CARGAR CONFIG.JSON
# ─────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"

def cargar_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    token_env = os.environ.get("DISCORD_TOKEN")
    if token_env:
        cfg["token"] = token_env
    if cfg.get("token") in ("", "TU_TOKEN_AQUÍ", None):
        log.critical("No se encontró token.")
        sys.exit(1)
    return cfg

CONFIG          = cargar_config()
TOKEN           = CONFIG["token"]
PREFIX          = CONFIG.get("prefix", "!")
ROLES_STAFF_CFG = CONFIG.get("roles_staff", ["👑 Administración", "🛡️ Moderador"])

# ─────────────────────────────────────────────────────────────
#  BOT
# ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

def _get_prefix(bot_instance, message):
    """Responde a ! (configurado), / y mención."""
    return commands.when_mentioned_or(PREFIX, "/")(bot_instance, message)

bot = commands.Bot(command_prefix=_get_prefix, intents=intents)
bot.remove_command("help")

# ─────────────────────────────────────────────────────────────
#  PERMISOS
# ─────────────────────────────────────────────────────────────
def es_admin(ctx) -> bool:
    return ctx.author.guild_permissions.administrator

def es_staff(ctx) -> bool:
    return (
        ctx.author.guild_permissions.administrator
        or ctx.author.guild_permissions.manage_roles
        or any(r.name in ROLES_STAFF_CFG for r in ctx.author.roles)
    )

def es_owner_o_admin(ctx) -> bool:
    return ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator

# ═════════════════════════════════════════════════════════════
#  🛡️ ANTINUKE — SISTEMA COMPLETO
# ═════════════════════════════════════════════════════════════

ANTINUKE_FILE = "antinuke.json"

ANTINUKE_DEFAULT = {
    "activo": True,
    "whitelist": [],
    "owner_id": None,
    "limites": {
        "ban": 3,
        "kick": 3,
        "roles": 3,
        "canales": 3,
        "webhooks": 3,
    },
    "ventana": 10,
    "accion": "ban",
    "log_channel": None,
    "antiraid": {
        "activo": False,
        "joins_limite": 10,
        "joins_ventana": 10,
        "accion": "kick",
    },
    "antilinks": {
        "activo": False,
        "whitelist_canales": [],
        "whitelist_roles": [],
    },
    "antispam": {
        "activo": False,
        "mensajes_limite": 5,
        "ventana": 5,
    },
    "antibot": {
        "activo": False,
    },
    "verificacion": {
        "activo": False,
        "rol_verificado": None,
        "rol_no_verificado": None,
        "canal": None,
        "emoji": "✅",
    },
    "warn_sistema": {},
    "mute_rol": None,
}

def _cargar_db_antinuke() -> dict:
    if os.path.exists(ANTINUKE_FILE):
        with open(ANTINUKE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _guardar_db_antinuke(db: dict):
    with open(ANTINUKE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def cargar_antinuke(guild_id: int = None) -> dict:
    db = _cargar_db_antinuke()
    key = str(guild_id) if guild_id else "__global__"
    data = db.get(key, {})
    import copy
    resultado = copy.deepcopy(ANTINUKE_DEFAULT)
    for k, v in data.items():
        if k == "limites" and isinstance(v, dict):
            resultado["limites"].update(v)
        else:
            resultado[k] = v
    return resultado

def guardar_antinuke(cfg: dict, guild_id: int = None):
    db = _cargar_db_antinuke()
    key = str(guild_id) if guild_id else "__global__"
    db[key] = cfg
    _guardar_db_antinuke(db)

# Contadores { guild_id: { user_id: [(timestamp, accion), ...] } }
_acciones      = defaultdict(lambda: defaultdict(list))
_joins_recents = defaultdict(list)
_spam_tracker  = defaultdict(lambda: defaultdict(list))

def registrar_accion(user_id: int, tipo: str, guild_id: int = 0) -> int:
    cfg     = cargar_antinuke(guild_id)
    ventana = cfg.get("ventana", 10)
    ahora   = time.time()
    _acciones[guild_id][user_id] = [
        (t, a) for t, a in _acciones[guild_id][user_id] if ahora - t <= ventana
    ]
    _acciones[guild_id][user_id].append((ahora, tipo))
    return sum(1 for _, a in _acciones[guild_id][user_id] if a == tipo)

def es_seguro(user_id: int, guild: discord.Guild) -> bool:
    cfg = cargar_antinuke(guild.id)
    if guild.owner_id == user_id:
        return True
    owner = cfg.get("owner_id")
    if owner and user_id == int(owner):
        return True
    return user_id in [int(x) for x in cfg.get("whitelist", [])]

def es_owner_an(ctx) -> bool:
    cfg   = cargar_antinuke(ctx.guild.id)
    owner = cfg.get("owner_id")
    return (
        ctx.author.id == ctx.guild.owner_id
        or (owner and ctx.author.id == int(owner))
    )

async def ejecutar_castigo(guild: discord.Guild, member, razon: str, accion: str = None):
    cfg = cargar_antinuke(guild.id)
    if accion is None:
        accion = cfg.get("accion", "ban")
    if isinstance(member, int):
        try:
            member = await guild.fetch_member(member)
        except Exception:
            try:
                user = await bot.fetch_user(member)
                if accion == "ban":
                    await guild.ban(user, reason=f"[AntiNuke] {razon}", delete_message_days=0)
                    log.warning(f"[AntiNuke] BAN (por ID) a {user} — {razon}")
            except Exception as e:
                log.error(f"[AntiNuke] No pude castigar ID {member}: {e}")
            return
    try:
        if accion == "ban":
            await guild.ban(member, reason=f"[AntiNuke] {razon}", delete_message_days=0)
        elif accion == "kick":
            await guild.kick(member, reason=f"[AntiNuke] {razon}")
        elif accion == "quitar_roles":
            roles = [r for r in member.roles if r != guild.default_role and not r.managed]
            if roles:
                await member.remove_roles(*roles, reason=f"[AntiNuke] {razon}")
        log.warning(f"[AntiNuke] {accion.upper()} a {member} — {razon}")
    except discord.Forbidden:
        log.error(f"[AntiNuke] Sin permisos para {accion} a {member}.")
    except Exception as e:
        log.error(f"[AntiNuke] No pude aplicar castigo a {member}: {e}")

async def log_antinuke(guild: discord.Guild, titulo: str, desc: str, color=0xFF0000):
    cfg = cargar_antinuke(guild.id)
    canal_id = cfg.get("log_channel")
    if not canal_id:
        return
    canal = guild.get_channel(int(canal_id))
    if canal:
        embed = discord.Embed(
            title=f"🛡️ AntiNuke — {titulo}",
            description=desc,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        try:
            await canal.send(embed=embed)
        except Exception:
            pass

# ── Eventos AntiNuke ──────────────────────────────────────────

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    cfg = cargar_antinuke(guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, guild):
            return
        count = registrar_accion(autor.id, "ban", guild.id)

        try:
            await guild.unban(user, reason=f"[AntiNuke] Ban no autorizado por {autor}")
            await log_antinuke(guild, "♻️ Ban Revertido",
                f"**Víctima:** {user.mention} (`{user.id}`)\n**Baneado por:** {autor.mention}\n**Acción:** Desbaneado automáticamente",
                color=0xFF0000)
        except Exception as e:
            log.error(f"[AntiNuke] No pude desbanear a {user}: {e}")

        try:
            m = guild.get_member(autor.id) or await guild.fetch_member(autor.id)
        except Exception:
            m = None
        if m:
            await ejecutar_castigo(guild, m, f"Ban no autorizado ({count} bans)")
            await log_antinuke(guild, "🔨 Ban No Autorizado Detectado",
                f"**Usuario:** {autor.mention} (`{autor.id}`)\n**Bans en ventana:** {count}\n**Acción:** `{cfg['accion']}`")
        else:
            try:
                await guild.ban(discord.Object(id=autor.id), reason=f"[AntiNuke] Ban no autorizado ({count} bans)")
                await log_antinuke(guild, "🔨 Ban No Autorizado (por ID)",
                    f"**Usuario:** {autor.mention} (`{autor.id}`)\n**Bans:** {count}\n**Acción:** BAN por ID")
            except Exception as e:
                log.error(f"[AntiNuke] No pude banear a {autor} por ID: {e}")
    except Exception as e:
        log.error(f"[AntiNuke] on_member_ban: {e}")

@bot.event
async def on_member_remove(member: discord.Member):
    cfg = cargar_antinuke(member.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, member.guild):
            return
        if entries[0].target.id != member.id:
            return
        count = registrar_accion(autor.id, "kick", member.guild.id)

        try:
            m = member.guild.get_member(autor.id) or await member.guild.fetch_member(autor.id)
        except Exception:
            m = None
        if m:
            await ejecutar_castigo(member.guild, m, f"Kick no autorizado ({count} kicks)")
            await log_antinuke(member.guild, "👢 Kick No Autorizado Detectado",
                f"**Usuario:** {autor.mention}\n**Kickeó a:** {member.mention}\n**Kicks en ventana:** {count}\n**Acción:** `{cfg['accion']}`")
        else:
            try:
                await member.guild.ban(discord.Object(id=autor.id), reason=f"[AntiNuke] Kick no autorizado ({count})")
                await log_antinuke(member.guild, "👢 Kick No Autorizado (por ID)",
                    f"**Usuario:** {autor.mention} (`{autor.id}`)\n**Kicks:** {count}\n**Acción:** BAN por ID")
            except Exception as e:
                log.error(f"[AntiNuke] No pude castigar a {autor} por ID: {e}")
    except Exception as e:
        log.error(f"[AntiNuke] on_member_remove: {e}")

@bot.event
async def on_guild_role_delete(role: discord.Role):
    cfg = cargar_antinuke(role.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, role.guild):
            return
        count = registrar_accion(autor.id, "roles", role.guild.id)

        try:
            nuevo_rol = await role.guild.create_role(
                name=role.name,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable,
                permissions=role.permissions,
                reason=f"[AntiNuke] Restaurando rol eliminado por {autor}"
            )
            try:
                await nuevo_rol.edit(position=role.position)
            except Exception:
                pass
            await log_antinuke(role.guild, "♻️ Rol Restaurado",
                f"**Rol:** `{role.name}`\n**Eliminado por:** {autor.mention}\n**Restaurado:** {nuevo_rol.mention}",
                color=0xFF0000)
        except Exception as e:
            log.error(f"[AntiNuke] No pude restaurar rol {role.name}: {e}")

        if count >= cfg["limites"]["roles"]:
            m = role.guild.get_member(autor.id) or await role.guild.fetch_member(autor.id)
            if m:
                await ejecutar_castigo(role.guild, m, f"Borrado masivo de roles ({count})")
                await log_antinuke(role.guild, "🗑️ Borrado de Roles Detectado",
                    f"**Usuario:** {autor.mention}\n**Roles borrados:** {count}\n**Acción:** `{cfg['accion']}`")
    except Exception as e:
        log.error(f"[AntiNuke] on_guild_role_delete: {e}")

@bot.event
async def on_guild_role_create(role: discord.Role):
    cfg = cargar_antinuke(role.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, role.guild):
            return
        count = registrar_accion(autor.id, "roles", role.guild.id)

        try:
            await role.delete(reason=f"[AntiNuke] Rol no autorizado creado por {autor}")
            await log_antinuke(role.guild, "🗑️ Rol No Autorizado Eliminado",
                f"**Rol:** `{role.name}`\n**Creado por:** {autor.mention}\n**Acción:** Eliminado automáticamente",
                color=0xFF0000)
        except Exception as e:
            log.error(f"[AntiNuke] No pude eliminar rol {role.name}: {e}")

        if count >= cfg["limites"]["roles"]:
            m = role.guild.get_member(autor.id) or await role.guild.fetch_member(autor.id)
            if m:
                await ejecutar_castigo(role.guild, m, f"Creación masiva de roles ({count})")
                await log_antinuke(role.guild, "🆕 Creación Masiva de Roles",
                    f"**Usuario:** {autor.mention}\n**Roles creados:** {count}\n**Acción:** `{cfg['accion']}`")
    except Exception as e:
        log.error(f"[AntiNuke] on_guild_role_create: {e}")

@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    pass

@bot.event
async def on_guild_channel_delete(channel):
    cfg = cargar_antinuke(channel.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, channel.guild):
            return
        count = registrar_accion(autor.id, "canales", channel.guild.id)

        try:
            overwrites = channel.overwrites
            if isinstance(channel, discord.TextChannel):
                nuevo_canal = await channel.guild.create_text_channel(
                    name=channel.name,
                    topic=channel.topic,
                    slowmode_delay=channel.slowmode_delay,
                    nsfw=channel.nsfw,
                    overwrites=overwrites,
                    category=channel.category,
                    reason=f"[AntiNuke] Restaurando canal eliminado por {autor}"
                )
            elif isinstance(channel, discord.VoiceChannel):
                nuevo_canal = await channel.guild.create_voice_channel(
                    name=channel.name,
                    bitrate=channel.bitrate,
                    user_limit=channel.user_limit,
                    overwrites=overwrites,
                    category=channel.category,
                    reason=f"[AntiNuke] Restaurando canal eliminado por {autor}"
                )
            elif isinstance(channel, discord.CategoryChannel):
                nuevo_canal = await channel.guild.create_category(
                    name=channel.name,
                    overwrites=overwrites,
                    reason=f"[AntiNuke] Restaurando categoría eliminada por {autor}"
                )
            else:
                nuevo_canal = await channel.guild.create_text_channel(
                    name=channel.name,
                    overwrites=overwrites,
                    category=channel.category,
                    reason=f"[AntiNuke] Restaurando canal eliminado por {autor}"
                )
            try:
                await nuevo_canal.edit(position=channel.position)
            except Exception:
                pass
            await log_antinuke(channel.guild, "♻️ Canal Restaurado",
                f"**Canal:** `#{channel.name}`\n**Eliminado por:** {autor.mention}\n**Restaurado:** {nuevo_canal.mention}",
                color=0xFF0000)
        except Exception as e:
            log.error(f"[AntiNuke] No pude restaurar canal {channel.name}: {e}")

        if count >= cfg["limites"]["canales"]:
            m = channel.guild.get_member(autor.id) or await channel.guild.fetch_member(autor.id)
            if m:
                await ejecutar_castigo(channel.guild, m, f"Borrado masivo de canales ({count})")
                await log_antinuke(channel.guild, "🗑️ Borrado de Canales Detectado",
                    f"**Usuario:** {autor.mention}\n**Canales borrados:** {count}\n**Acción:** `{cfg['accion']}`")
    except Exception as e:
        log.error(f"[AntiNuke] on_guild_channel_delete: {e}")

@bot.event
async def on_guild_channel_create(channel):
    cfg = cargar_antinuke(channel.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, channel.guild):
            return
        count = registrar_accion(autor.id, "canales", channel.guild.id)

        try:
            nombre = channel.name
            await channel.delete(reason=f"[AntiNuke] Canal no autorizado creado por {autor}")
            await log_antinuke(channel.guild, "🗑️ Canal No Autorizado Eliminado",
                f"**Canal:** `#{nombre}`\n**Creado por:** {autor.mention}\n**Acción:** Eliminado automáticamente",
                color=0xFF0000)
        except Exception as e:
            log.error(f"[AntiNuke] No pude eliminar canal {channel.name}: {e}")

        if count >= cfg["limites"]["canales"]:
            m = channel.guild.get_member(autor.id) or await channel.guild.fetch_member(autor.id)
            if m:
                await ejecutar_castigo(channel.guild, m, f"Creación masiva de canales ({count})")
                await log_antinuke(channel.guild, "🆕 Creación Masiva de Canales",
                    f"**Usuario:** {autor.mention}\n**Canales creados:** {count}\n**Acción:** `{cfg['accion']}`")
    except Exception as e:
        log.error(f"[AntiNuke] on_guild_channel_create: {e}")

@bot.event
async def on_webhooks_update(channel):
    cfg = cargar_antinuke(channel.guild.id)
    if not cfg.get("activo"):
        return
    await asyncio.sleep(0.5)
    try:
        entries = [e async for e in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.webhook_create)]
        if not entries:
            return
        autor = entries[0].user
        if autor.bot or es_seguro(autor.id, channel.guild):
            return
        count = registrar_accion(autor.id, "webhooks", channel.guild.id)
        if count >= cfg["limites"]["webhooks"]:
            m = channel.guild.get_member(autor.id) or await channel.guild.fetch_member(autor.id)
            if m:
                await ejecutar_castigo(channel.guild, m, f"Creación masiva de webhooks ({count})")
                await log_antinuke(channel.guild, "🕸️ Webhooks Masivos",
                    f"**Usuario:** {autor.mention}\n**Webhooks:** {count}\n**Acción:** `{cfg['accion']}`")
    except Exception as e:
        log.error(f"[AntiNuke] on_webhooks_update: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    cfg = cargar_antinuke(member.guild.id)

    if cfg.get("antibot", {}).get("activo") and member.bot:
        try:
            entry = await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add).next()
            autor = entry.user
            if not es_seguro(autor.id, member.guild):
                await member.kick(reason="[AntiBot] Bot no autorizado")
                await log_antinuke(member.guild, "🤖 Bot No Autorizado",
                    f"**Bot:** {member.mention}\n**Añadido por:** {autor.mention}", color=0xFF0000)
                return
        except Exception:
            pass

    ar = cfg.get("antiraid", {})
    if ar.get("activo"):
        ahora   = time.time()
        gid     = member.guild.id
        ventana = ar.get("joins_ventana", 10)
        _joins_recents[gid].append(ahora)
        while _joins_recents[gid] and ahora - _joins_recents[gid][0] > ventana:
            _joins_recents[gid].pop(0)
        if len(_joins_recents[gid]) >= ar.get("joins_limite", 10):
            accion = ar.get("accion", "kick")
            try:
                if accion == "kick":
                    await member.kick(reason="[AntiRaid] Raid detectada")
                elif accion == "ban":
                    await member.ban(reason="[AntiRaid] Raid detectada", delete_message_days=0)
            except Exception:
                pass
            await log_antinuke(member.guild, "🚨 Raid Detectada",
                f"**Joins en {ventana}s:** {len(_joins_recents[gid])}\n**Último:** {member.mention}\n**Acción:** `{accion}`",
                color=0xFF0000)

    ver = cfg.get("verificacion", {})
    if ver.get("activo") and ver.get("rol_no_verificado"):
        rol = member.guild.get_role(int(ver["rol_no_verificado"]))
        if rol:
            try:
                await member.add_roles(rol)
            except Exception:
                pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    cfg = cargar_antinuke(message.guild.id)

    al = cfg.get("antilinks", {})
    if al.get("activo"):
        wl_canales = [int(x) for x in al.get("whitelist_canales", [])]
        wl_roles   = [int(x) for x in al.get("whitelist_roles", [])]
        tiene_link = any(x in message.content for x in ["http://", "https://", "discord.gg/", "discord.com/invite/"])
        in_wl_canal = message.channel.id in wl_canales
        in_wl_rol   = any(r.id in wl_roles for r in message.author.roles)
        es_safe_usr = es_seguro(message.author.id, message.guild)
        if tiene_link and not in_wl_canal and not in_wl_rol and not es_safe_usr:
            try:
                await message.delete()
                await message.channel.send(f"🔗 {message.author.mention} No se permiten links aquí.", delete_after=5)
                await log_antinuke(message.guild, "🔗 Link Bloqueado",
                    f"**Usuario:** {message.author.mention}\n**Canal:** {message.channel.mention}", color=0xFF0000)
            except Exception:
                pass
            return

    asp = cfg.get("antispam", {})
    if asp.get("activo") and not es_seguro(message.author.id, message.guild):
        ahora   = time.time()
        ventana = asp.get("ventana", 5)
        limite  = asp.get("mensajes_limite", 5)
        gid     = message.guild.id
        uid     = message.author.id
        _spam_tracker[gid][uid] = [t for t in _spam_tracker[gid][uid] if ahora - t <= ventana]
        _spam_tracker[gid][uid].append(ahora)
        if len(_spam_tracker[gid][uid]) >= limite:
            try:
                import datetime as dt
                until = discord.utils.utcnow() + dt.timedelta(minutes=5)
                await message.author.timeout(until, reason="[AntiSpam] Spam detectado")
                await message.channel.send(f"🔇 {message.author.mention} fue silenciado por spam.", delete_after=5)
                _spam_tracker[gid][uid] = []
                await log_antinuke(message.guild, "💬 Spam Detectado",
                    f"**Usuario:** {message.author.mention}\n**Canal:** {message.channel.mention}", color=0xFF0000)
            except Exception:
                pass

    await bot.process_commands(message)

# ── Verificación por reacción ──────────────────────────────────

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    cfg = cargar_antinuke(payload.guild_id)
    ver = cfg.get("verificacion", {})
    if not ver.get("activo"):
        return
    canal_id = ver.get("canal")
    if not canal_id or payload.channel_id != int(canal_id):
        return
    if str(payload.emoji) != ver.get("emoji", "✅"):
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    rol_ver = ver.get("rol_verificado")
    rol_no  = ver.get("rol_no_verificado")
    if rol_ver:
        r = guild.get_role(int(rol_ver))
        if r:
            try:
                await member.add_roles(r, reason="Verificación")
            except Exception:
                pass
    if rol_no:
        r = guild.get_role(int(rol_no))
        if r and r in member.roles:
            try:
                await member.remove_roles(r, reason="Verificación")
            except Exception:
                pass

# ══════════════════════════════════════════════════════════════
#  🛡️ COMANDOS ANTINUKE (solo Owner del AntiNuke)
# ══════════════════════════════════════════════════════════════

@bot.command(name="antinuke")
@commands.check(es_owner_an)
async def antinuke_status(ctx):
    cfg    = cargar_antinuke(ctx.guild.id)
    estado = "✅ Activo" if cfg["activo"] else "❌ Desactivado"

    wl = cfg.get("whitelist", [])
    wl_members = []
    for uid in wl:
        m = ctx.guild.get_member(int(uid))
        if m:
            wl_members.append(m.mention)
    wl_txt = ", ".join(wl_members) if wl_members else "Nadie"

    embed = discord.Embed(title="🛡️ AntiNuke — Panel Completo", color=0xFF0000 if cfg["activo"] else 0xFF0000)
    embed.add_field(name="Estado",   value=estado,                            inline=True)
    embed.add_field(name="Acción",   value=cfg.get("accion", "ban").upper(),  inline=True)
    embed.add_field(name="Ventana",  value=f"{cfg.get('ventana', 10)}s",      inline=True)
    lim = cfg.get("limites", {})
    embed.add_field(name="Límites",
        value="\n".join(f"`{k}`: {v}" for k, v in lim.items()), inline=True)
    ar  = cfg.get("antiraid", {})
    al  = cfg.get("antilinks", {})
    asp = cfg.get("antispam", {})
    ab  = cfg.get("antibot", {})
    embed.add_field(name="Módulos",
        value=(
            f"AntiRaid: {'✅' if ar.get('activo') else '❌'}\n"
            f"AntiLinks: {'✅' if al.get('activo') else '❌'}\n"
            f"AntiSpam: {'✅' if asp.get('activo') else '❌'}\n"
            f"AntiBot: {'✅' if ab.get('activo') else '❌'}"
        ), inline=True)
    embed.add_field(name=f"Whitelist ({len(wl_members)})", value=wl_txt, inline=False)
    log_ch = cfg.get("log_channel")
    embed.add_field(name="Canal logs", value=f"<#{log_ch}>" if log_ch else "No configurado", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="an_ayuda")
@commands.check(es_owner_an)
async def an_ayuda(ctx):
    p = PREFIX
    embed = discord.Embed(title="🛡️ AntiNuke — Comandos", color=0xFF0000)
    embed.add_field(name="⚙️ General",
        value=(
            f"`{p}antinuke` — Panel de estado\n"
            f"`{p}an_activar` / `{p}an_desactivar` — Activar/desactivar\n"
            f"`{p}an_accion <ban|kick|quitar_roles>` — Acción al detectar\n"
            f"`{p}an_limite <tipo> <n>` — Cambiar límite\n"
            f"`{p}an_ventana <segundos>` — Ventana de tiempo\n"
            f"`{p}an_whitelist @user` — Añadir/quitar de whitelist\n"
            f"`{p}an_logs [#canal]` — Canal de logs\n"
            f"`{p}an_owner @user` — Asignar owner del AN"
        ), inline=False)
    embed.add_field(name="🚨 AntiRaid",
        value=(
            f"`{p}an_antiraid` — Ver estado\n"
            f"`{p}an_antiraid_on` / `{p}an_antiraid_off` — Activar/desactivar\n"
            f"`{p}an_antiraid_config <joins> <ventana> <accion>` — Configurar"
        ), inline=False)
    embed.add_field(name="🔗 AntiLinks",
        value=(
            f"`{p}an_antilinks_on` / `{p}an_antilinks_off` — Activar/desactivar\n"
            f"`{p}an_links_canal #canal` — Whitelist canal\n"
            f"`{p}an_links_rol <rol>` — Whitelist rol"
        ), inline=False)
    embed.add_field(name="💬 AntiSpam",
        value=(
            f"`{p}an_antispam_on` / `{p}an_antispam_off` — Activar/desactivar\n"
            f"`{p}an_spam_config <mensajes> <ventana>` — Configurar"
        ), inline=False)
    embed.add_field(name="🤖 AntiBot / ✅ Verificación",
        value=(
            f"`{p}an_antibot_on` / `{p}an_antibot_off` — Bloquear bots no autorizados\n"
            f"`{p}an_ver_setup #canal @rol_verificado @rol_no_verificado` — Setup verificación\n"
            f"`{p}an_ver_on` / `{p}an_ver_off` — Activar/desactivar verificación"
        ), inline=False)
    embed.add_field(name="⚠️ Warns",
        value=(
            f"`{p}warn @user <razón>` — Advertir usuario\n"
            f"`{p}warns @user` — Ver advertencias\n"
            f"`{p}clearwarns @user` — Borrar advertencias"
        ), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="an_activar")
@commands.check(es_owner_an)
async def an_activar(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ AntiNuke **activado**.")

@bot.command(name="an_desactivar")
@commands.check(es_owner_an)
async def an_desactivar(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ AntiNuke **desactivado**. El servidor queda sin protección.")

@bot.command(name="an_whitelist")
@commands.check(es_owner_an)
async def an_whitelist(ctx, member: discord.Member = None):
    cfg = cargar_antinuke(ctx.guild.id)
    wl  = cfg.get("whitelist", [])

    if member is None:
        wl_members = []
        for uid in wl:
            m = ctx.guild.get_member(int(uid))
            if m:
                wl_members.append(f"{m.mention} (`{m.id}`)")
        embed = discord.Embed(
            title=f"🛡️ Whitelist — {ctx.guild.name}",
            description="\n".join(wl_members) if wl_members else "Nadie en la whitelist.",
            color=0xFF0000
        )
        return await ctx.send(embed=embed)

    uid = str(member.id)
    if uid in wl:
        wl.remove(uid)
        cfg["whitelist"] = wl
        guardar_antinuke(cfg, ctx.guild.id)
        embed = discord.Embed(
            title="🗑️ Quitado de Whitelist",
            description=f"{member.mention} ya **no está** en la whitelist de **{ctx.guild.name}**.",
            color=discord.Color.red()
        )
    else:
        wl.append(uid)
        cfg["whitelist"] = wl
        guardar_antinuke(cfg, ctx.guild.id)
        embed = discord.Embed(
            title="✅ Añadido a Whitelist",
            description=f"{member.mention} ahora está en la whitelist de **{ctx.guild.name}**.\nEl AntiNuke lo ignorará en este servidor.",
            color=discord.Color.red()
        )
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="an_accion")
@commands.check(es_owner_an)
async def an_accion(ctx, accion: str):
    accion = accion.lower()
    if accion not in ("ban", "kick", "quitar_roles"):
        return await ctx.send("❌ Opciones: `ban`, `kick`, `quitar_roles`")
    cfg = cargar_antinuke(ctx.guild.id); cfg["accion"] = accion; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ Acción → **{accion.upper()}**.")

@bot.command(name="an_limite")
@commands.check(es_owner_an)
async def an_limite(ctx, tipo: str, cantidad: int):
    tipos = list(ANTINUKE_DEFAULT["limites"].keys())
    if tipo not in tipos:
        return await ctx.send(f"❌ Tipos: {', '.join(f'`{t}`' for t in tipos)}")
    if not 0 <= cantidad <= 20:
        return await ctx.send("❌ Entre 0 y 20.")
    cfg = cargar_antinuke(ctx.guild.id); cfg["limites"][tipo] = cantidad; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ Límite `{tipo}` → **{cantidad}**.")

@bot.command(name="an_ventana")
@commands.check(es_owner_an)
async def an_ventana(ctx, segundos: int):
    if not 5 <= segundos <= 120:
        return await ctx.send("❌ Entre 5 y 120 segundos.")
    cfg = cargar_antinuke(ctx.guild.id); cfg["ventana"] = segundos; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ Ventana → **{segundos}s**.")

@bot.command(name="an_logs")
@commands.check(es_owner_an)
async def an_logs(ctx, canal: discord.TextChannel = None):
    cfg = cargar_antinuke(ctx.guild.id)
    if canal is None:
        cfg["log_channel"] = None; guardar_antinuke(cfg, ctx.guild.id)
        return await ctx.send("🗑️ Canal de logs **eliminado**.")
    cfg["log_channel"] = str(canal.id); guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ Canal de logs → {canal.mention}.")

@bot.command(name="an_owner")
@commands.check(lambda ctx: ctx.author.id == ctx.guild.owner_id)
async def an_owner(ctx, member: discord.Member):
    cfg = cargar_antinuke(ctx.guild.id); cfg["owner_id"] = str(member.id); guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ {member.mention} es ahora el **owner del AntiNuke**.")

# ── AntiRaid ───────────────────────────────────────────────────

@bot.command(name="an_antiraid")
@commands.check(es_owner_an)
async def an_antiraid_status(ctx):
    cfg = cargar_antinuke(ctx.guild.id)
    ar  = cfg.get("antiraid", {})
    embed = discord.Embed(title="🚨 AntiRaid", color=0xFF0000 if ar.get("activo") else 0xFF0000)
    embed.add_field(name="Estado",   value="✅ Activo" if ar.get("activo") else "❌ Desactivado", inline=True)
    embed.add_field(name="Límite",   value=f"{ar.get('joins_limite',10)} joins", inline=True)
    embed.add_field(name="Ventana",  value=f"{ar.get('joins_ventana',10)}s",     inline=True)
    embed.add_field(name="Acción",   value=ar.get("accion","kick").upper(),      inline=True)
    await ctx.send(embed=embed)

@bot.command(name="an_antiraid_on")
@commands.check(es_owner_an)
async def an_antiraid_on(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antiraid", {})["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ AntiRaid **activado**.")

@bot.command(name="an_antiraid_off")
@commands.check(es_owner_an)
async def an_antiraid_off(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antiraid", {})["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ AntiRaid **desactivado**.")

@bot.command(name="an_antiraid_config")
@commands.check(es_owner_an)
async def an_antiraid_config(ctx, joins: int, ventana: int, accion: str = "kick"):
    if accion not in ("kick", "ban"):
        return await ctx.send("❌ Acción: `kick` o `ban`")
    cfg = cargar_antinuke(ctx.guild.id)
    cfg.setdefault("antiraid", {}).update({"joins_limite": joins, "joins_ventana": ventana, "accion": accion})
    guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ AntiRaid → **{joins} joins** en **{ventana}s** → **{accion}**.")

# ── AntiLinks ──────────────────────────────────────────────────

@bot.command(name="an_antilinks_on")
@commands.check(es_owner_an)
async def an_antilinks_on(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antilinks", {})["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ AntiLinks **activado**.")

@bot.command(name="an_antilinks_off")
@commands.check(es_owner_an)
async def an_antilinks_off(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antilinks", {})["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ AntiLinks **desactivado**.")

@bot.command(name="an_links_canal")
@commands.check(es_owner_an)
async def an_links_canal(ctx, canal: discord.TextChannel):
    cfg = cargar_antinuke(ctx.guild.id)
    wl  = cfg.setdefault("antilinks", {}).setdefault("whitelist_canales", [])
    cid = str(canal.id)
    if cid in wl: wl.remove(cid); accion = "quitado de"
    else: wl.append(cid); accion = "añadido a"
    guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ {canal.mention} **{accion}** la whitelist de links.")

@bot.command(name="an_links_rol")
@commands.check(es_owner_an)
async def an_links_rol(ctx, *, nombre_rol: str):
    rol = discord.utils.get(ctx.guild.roles, name=nombre_rol)
    if not rol:
        return await ctx.send(f"❌ Rol `{nombre_rol}` no encontrado.")
    cfg = cargar_antinuke(ctx.guild.id)
    wl  = cfg.setdefault("antilinks", {}).setdefault("whitelist_roles", [])
    rid = str(rol.id)
    if rid in wl: wl.remove(rid); accion = "quitado de"
    else: wl.append(rid); accion = "añadido a"
    guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ **{rol.name}** **{accion}** la whitelist de links.")

# ── AntiSpam ───────────────────────────────────────────────────

@bot.command(name="an_antispam_on")
@commands.check(es_owner_an)
async def an_antispam_on(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antispam", {})["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ AntiSpam **activado**.")

@bot.command(name="an_antispam_off")
@commands.check(es_owner_an)
async def an_antispam_off(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antispam", {})["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ AntiSpam **desactivado**.")

@bot.command(name="an_spam_config")
@commands.check(es_owner_an)
async def an_spam_config(ctx, mensajes: int, ventana: int):
    if not 3 <= mensajes <= 20 or not 3 <= ventana <= 30:
        return await ctx.send("❌ mensajes: 3–20 | ventana: 3–30s")
    cfg = cargar_antinuke(ctx.guild.id)
    cfg.setdefault("antispam", {}).update({"mensajes_limite": mensajes, "ventana": ventana})
    guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send(f"✅ AntiSpam → **{mensajes} msgs** en **{ventana}s**.")

# ── AntiBot ────────────────────────────────────────────────────

@bot.command(name="an_antibot_on")
@commands.check(es_owner_an)
async def an_antibot_on(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antibot", {})["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ AntiBot **activado**. Bots no autorizados serán expulsados.")

@bot.command(name="an_antibot_off")
@commands.check(es_owner_an)
async def an_antibot_off(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("antibot", {})["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ AntiBot **desactivado**.")

# ── Verificación ───────────────────────────────────────────────

@bot.command(name="an_ver_setup")
@commands.check(es_owner_an)
async def an_ver_setup(ctx, canal: discord.TextChannel, rol_ver: discord.Role, rol_no_ver: discord.Role = None):
    cfg = cargar_antinuke(ctx.guild.id)
    cfg.setdefault("verificacion", {}).update({
        "canal": str(canal.id),
        "rol_verificado": str(rol_ver.id),
        "rol_no_verificado": str(rol_no_ver.id) if rol_no_ver else None,
    })
    guardar_antinuke(cfg, ctx.guild.id)
    embed = discord.Embed(
        title="✅ Verificación",
        description=f"Reacciona con ✅ para verificarte y acceder al servidor.",
        color=discord.Color.red()
    )
    msg = await canal.send(embed=embed)
    await msg.add_reaction("✅")
    await ctx.send(f"✅ Verificación configurada en {canal.mention}.")

@bot.command(name="an_ver_on")
@commands.check(es_owner_an)
async def an_ver_on(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("verificacion", {})["activo"] = True; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("✅ Verificación **activada**.")

@bot.command(name="an_ver_off")
@commands.check(es_owner_an)
async def an_ver_off(ctx):
    cfg = cargar_antinuke(ctx.guild.id); cfg.setdefault("verificacion", {})["activo"] = False; guardar_antinuke(cfg, ctx.guild.id)
    await ctx.send("⚠️ Verificación **desactivada**.")

# ── Sistema de Warns ───────────────────────────────────────────

WARNS_FILE = "warns.json"

def cargar_warns() -> dict:
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_warns(data: dict):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@bot.command(name="warn")
@commands.check(es_staff)
async def warn(ctx, member: discord.Member, *, razon: str = "Sin razón"):
    if member.guild_permissions.administrator:
        return await ctx.send("❌ No puedes advertir a un administrador.")
    data = cargar_warns()
    uid  = str(member.id)
    if uid not in data:
        data[uid] = []
    data[uid].append({
        "razon": razon,
        "por": str(ctx.author.id),
        "fecha": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
    })
    guardar_warns(data)
    total = len(data[uid])
    embed = discord.Embed(title="⚠️ Advertencia", color=discord.Color.red())
    embed.add_field(name="👤 Usuario",  value=member.mention,    inline=True)
    embed.add_field(name="📋 Razón",    value=razon,              inline=True)
    embed.add_field(name="📊 Total",    value=f"{total} warn(s)", inline=True)
    embed.add_field(name="👮 Por",      value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)
    if total >= 5:
        await ctx.guild.ban(member, reason="[AutoWarn] 5 advertencias")
        await ctx.send(f"🔨 {member.mention} fue baneado automáticamente por alcanzar 5 warns.")
    elif total >= 3:
        import datetime as dt
        until = discord.utils.utcnow() + dt.timedelta(hours=1)
        try:
            await member.timeout(until, reason="[AutoWarn] 3 advertencias")
            await ctx.send(f"🔇 {member.mention} muteado 1h por 3 warns.")
        except Exception:
            pass

@bot.command(name="warns")
@commands.check(es_staff)
async def ver_warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    data   = cargar_warns()
    lista  = data.get(str(member.id), [])
    embed  = discord.Embed(title=f"⚠️ Warns de {member.display_name}", color=discord.Color.red())
    embed.set_thumbnail(url=member.display_avatar.url)
    if not lista:
        embed.description = "✅ Sin advertencias."
    else:
        for i, w in enumerate(lista, 1):
            embed.add_field(
                name=f"#{i} — {w['fecha']}",
                value=f"**Razón:** {w['razon']}\n**Por:** <@{w['por']}>",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command(name="clearwarns", aliases=["limpiarwarns"])
@commands.check(es_admin)
async def clearwarns(ctx, member: discord.Member):
    data = cargar_warns()
    data.pop(str(member.id), None)
    guardar_warns(data)
    await ctx.send(f"✅ Warns de {member.mention} borrados.")

@bot.command(name="delwarn")
@commands.check(es_admin)
async def delwarn(ctx, member: discord.Member, numero: int):
    data = cargar_warns()
    uid  = str(member.id)
    lista = data.get(uid, [])
    if numero < 1 or numero > len(lista):
        return await ctx.send(f"❌ Número inválido. Tiene {len(lista)} warn(s).")
    borrado = lista.pop(numero - 1)
    data[uid] = lista
    guardar_warns(data)
    await ctx.send(f"✅ Warn #{numero} de {member.mention} borrado. (`{borrado['razon']}`)")


# ═════════════════════════════════════════════════════════════
#  🎭 ROLEPLAY
# ═════════════════════════════════════════════════════════════

PAREJAS_FILE = "parejas.json"
FAMILIA_FILE  = "familia.json"

def cargar_parejas() -> dict:
    if os.path.exists(PAREJAS_FILE):
        with open(PAREJAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_parejas(data: dict):
    with open(PAREJAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def cargar_familia() -> dict:
    if os.path.exists(FAMILIA_FILE):
        with open(FAMILIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_familia(data: dict):
    with open(FAMILIA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

propuestas_pendientes = {}

@bot.command(name="casar", aliases=["proponer", "marry"])
async def casar(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ No puedes casarte contigo mismo.")
    if member.bot:
        return await ctx.send("❌ Los bots no se casan.")
    parejas = cargar_parejas()
    uid = str(ctx.author.id); mid = str(member.id)
    if uid in parejas:
        return await ctx.send(f"💍 Ya estás casado/a. Usa `{PREFIX}divorcio` primero.")
    if mid in parejas:
        return await ctx.send(f"💔 {member.mention} ya está casado/a.")
    propuestas_pendientes[member.id] = ctx.author.id
    embed = discord.Embed(title="💍 ¡Propuesta!", description=f"{ctx.author.mention} le propone a {member.mention}\nUsa `{PREFIX}aceptar` o `{PREFIX}rechazar` en 60s.", color=discord.Color.red())
    await ctx.send(embed=embed)
    await asyncio.sleep(60)
    if propuestas_pendientes.get(member.id) == ctx.author.id:
        propuestas_pendientes.pop(member.id, None)
        await ctx.send(f"⌛ La propuesta a {member.mention} expiró.")

@bot.command(name="aceptar")
async def aceptar(ctx):
    if ctx.author.id not in propuestas_pendientes:
        return await ctx.send("❌ Sin propuesta pendiente.")
    autor_id = propuestas_pendientes.pop(ctx.author.id)
    parejas  = cargar_parejas()
    mid = str(ctx.author.id)
    parejas[str(autor_id)] = mid; parejas[mid] = str(autor_id)
    guardar_parejas(parejas)
    embed = discord.Embed(title="💒 ¡Se casaron!", description=f"{ctx.author.mention} y <@{autor_id}> ¡Felicidades! 🎉", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="rechazar")
async def rechazar(ctx):
    if ctx.author.id not in propuestas_pendientes:
        return await ctx.send("❌ Sin propuesta pendiente.")
    autor_id = propuestas_pendientes.pop(ctx.author.id)
    await ctx.send(f"💔 {ctx.author.mention} rechazó a <@{autor_id}>.")

@bot.command(name="divorcio", aliases=["divorciar"])
async def divorcio(ctx):
    parejas = cargar_parejas(); uid = str(ctx.author.id)
    if uid not in parejas:
        return await ctx.send("❌ No estás casado/a.")
    ex_id = parejas.pop(uid); parejas.pop(str(ex_id), None)
    guardar_parejas(parejas)
    embed = discord.Embed(title="💔 Divorcio", description=f"{ctx.author.mention} se divorció de <@{ex_id}>.", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="pareja", aliases=["esposo", "esposa"])
async def ver_pareja(ctx, member: discord.Member = None):
    member = member or ctx.author
    parejas = cargar_parejas(); uid = str(member.id)
    if uid not in parejas:
        return await ctx.send(f"💔 {member.display_name} no está casado/a.")
    embed = discord.Embed(title="💍 Estado Civil", description=f"{member.mention} está con <@{parejas[uid]}> 💕", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="adoptar")
async def adoptar(ctx, member: discord.Member):
    if member == ctx.author or member.bot:
        return await ctx.send("❌ No puedes adoptarte a ti mismo ni a un bot.")
    familia = cargar_familia(); uid = str(ctx.author.id); mid = str(member.id)
    hijos = familia.get(uid, [])
    if mid in hijos:
        return await ctx.send(f"❌ {member.mention} ya es tu hijo/a.")
    hijos.append(mid); familia[uid] = hijos; guardar_familia(familia)
    embed = discord.Embed(title="👨‍👧 ¡Adopción!", description=f"{ctx.author.mention} adoptó a {member.mention} 💕", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="familia")
async def ver_familia(ctx, member: discord.Member = None):
    member = member or ctx.author
    familia = cargar_familia(); parejas = cargar_parejas(); uid = str(member.id)
    hijos = familia.get(uid, []); pareja = parejas.get(uid)
    embed = discord.Embed(title=f"👨‍👩‍👧 Familia de {member.display_name}", color=discord.Color.red())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="💍 Pareja", value=f"<@{pareja}>" if pareja else "Soltero/a", inline=False)
    embed.add_field(name="👶 Hijos", value="\n".join(f"<@{h}>" for h in hijos) if hijos else "Sin hijos", inline=False)
    await ctx.send(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🔮 HORÓSCOPO Y PERSONALIDAD
# ═════════════════════════════════════════════════════════════

SIGNOS = {
    "aries": ("♈","21 mar – 19 abr","Valiente, apasionado y directo."),
    "tauro": ("♉","20 abr – 20 may","Leal, paciente y determinado."),
    "geminis": ("♊","21 may – 20 jun","Curioso, adaptable y comunicativo."),
    "cancer": ("♋","21 jun – 22 jul","Intuitivo, protector y empático."),
    "leo": ("♌","23 jul – 22 ago","Carismático, generoso y líder nato."),
    "virgo": ("♍","23 ago – 22 sep","Analítico, detallista y perfeccionista."),
    "libra": ("♎","23 sep – 22 oct","Justo, diplomático y encantador."),
    "escorpio": ("♏","23 oct – 21 nov","Intenso, misterioso y poderoso."),
    "sagitario": ("♐","22 nov – 21 dic","Aventurero, optimista y filosófico."),
    "capricornio": ("♑","22 dic – 19 ene","Ambicioso, disciplinado y responsable."),
    "acuario": ("♒","20 ene – 18 feb","Innovador, independiente y humanitario."),
    "piscis": ("♓","19 feb – 20 mar","Compasivo, artístico y soñador."),
}
PREDICCIONES = [
    "🌟 Un encuentro inesperado cambiará tu día.",
    "💰 El dinero fluye si actúas con confianza.",
    "❤️ El amor está más cerca de lo que crees.",
    "⚠️ Evita decisiones impulsivas hoy.",
    "🎯 Tu concentración está al máximo.",
    "🌈 Buen día para empezar algo nuevo.",
    "🤝 Una amistad te sorprenderá positivamente.",
    "🔥 Tu energía es imparable, úsala bien.",
    "🌙 La noche traerá claridad a tus dudas.",
]

@bot.command(name="horoscopo", aliases=["signo","zodiac"])
async def horoscopo(ctx, *, signo: str):
    signo = signo.lower().strip()
    if signo not in SIGNOS:
        return await ctx.send(f"❌ Opciones: {', '.join(f'`{s}`' for s in SIGNOS)}")
    emoji, fechas, desc = SIGNOS[signo]
    embed = discord.Embed(title=f"{emoji} {signo.capitalize()}", color=0xFF0000)
    embed.add_field(name="📅 Fechas", value=fechas, inline=True)
    embed.add_field(name="🍀 Suerte", value=f"{random.randint(1,100)}%", inline=True)
    embed.add_field(name="✨ Personalidad", value=desc, inline=False)
    embed.add_field(name="🔮 Predicción", value=random.choice(PREDICCIONES), inline=False)
    await ctx.send(embed=embed)

TIPOS_PERSONALIDAD = [
    ("🔥 Alma de Fuego","Intenso/a, apasionado/a y siempre vas al frente."),
    ("🌊 Espíritu del Agua","Tranquilo/a, profundo/a y adaptable."),
    ("🌪️ Mente del Viento","Veloz, creativo/a y lleno/a de ideas."),
    ("🌍 Corazón de Tierra","Estable, confiable y roca para todos."),
    ("⚡ Rayo de Energía","Energía inagotable que contagia a todos."),
    ("🌙 Alma Lunar","Misterioso/a, intuitivo/a y emocional."),
    ("☀️ Espíritu Solar","Irradias positividad y alegría."),
    ("❄️ Mente de Hielo","Frío/a bajo presión y muy analítico/a."),
]

@bot.command(name="personalidad", aliases=["quiensoy","tipo"])
async def personalidad(ctx, member: discord.Member = None):
    member = member or ctx.author
    random.seed(member.id + datetime.now(timezone.utc).toordinal())
    tipo, desc = random.choice(TIPOS_PERSONALIDAD)
    random.seed()
    embed = discord.Embed(title=f"🔮 {member.display_name}", description=f"**{tipo}**\n\n{desc}", color=discord.Color.red())
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="compatibilidad", aliases=["compat","shipper"])
async def compatibilidad(ctx, member: discord.Member):
    ids = sorted([ctx.author.id, member.id])
    random.seed(ids[0] + ids[1])
    pct = random.randint(1, 100)
    random.seed()
    if pct >= 80:   estado = "💞 ¡Almas gemelas!"; color = discord.Color.red()
    elif pct >= 60: estado = "💕 Buena compatibilidad"; color = discord.Color.red()
    elif pct >= 40: estado = "🤝 Compatible con esfuerzo"; color = discord.Color.red()
    else:           estado = "💔 Difícil combinación"; color = discord.Color.red()
    barra = "█"*(pct//10) + "░"*(10-pct//10)
    embed = discord.Embed(title="💘 Compatibilidad", color=color)
    embed.add_field(name="👫 Pareja", value=f"{ctx.author.mention} & {member.mention}", inline=False)
    embed.add_field(name="📊 Resultado", value=f"`{barra}` **{pct}%**", inline=False)
    embed.add_field(name="💬 Estado", value=estado, inline=False)
    await ctx.send(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🃏 TRIVIA Y ADIVINA EL NÚMERO
# ═════════════════════════════════════════════════════════════

juegos_activos = {}

PREGUNTAS_TRIVIA = [
    {"p":"¿Cuántos lados tiene un hexágono?","r":"6","ops":["4","5","6","8"]},
    {"p":"¿Capital de Japón?","r":"tokio","ops":["osaka","tokio","beijing","seul"]},
    {"p":"¿Planetas en el sistema solar?","r":"8","ops":["7","8","9","10"]},
    {"p":"¿Año del hombre en la luna?","r":"1969","ops":["1965","1969","1971","1973"]},
    {"p":"¿Elemento más abundante en el universo?","r":"hidrogeno","ops":["oxigeno","helio","hidrogeno","carbono"]},
    {"p":"¿Colores del arcoíris?","r":"7","ops":["5","6","7","8"]},
    {"p":"¿Animal más rápido del mundo?","r":"guepardo","ops":["leon","guepardo","tigre","aguila"]},
    {"p":"¿Océano más grande?","r":"pacifico","ops":["atlantico","indico","pacifico","artico"]},
    {"p":"¿Huesos del cuerpo humano adulto?","r":"206","ops":["180","196","206","220"]},
    {"p":"¿País más grande del mundo?","r":"rusia","ops":["canada","china","rusia","eeuu"]},
    {"p":"¿Planeta rojo?","r":"marte","ops":["venus","marte","jupiter","saturno"]},
    {"p":"¿Cuánto es 15 x 15?","r":"225","ops":["200","215","225","250"]},
    {"p":"¿Metal más caro del mundo?","r":"rodio","ops":["oro","platino","rodio","iridio"]},
    {"p":"¿Continente de Brasil?","r":"america del sur","ops":["africa","america central","america del sur","europa"]},
    {"p":"¿Segundos en una hora?","r":"3600","ops":["1200","3000","3600","4800"]},
]

@bot.command(name="trivia")
async def trivia(ctx):
    if ctx.channel.id in juegos_activos:
        return await ctx.send("❌ Ya hay una trivia activa.")
    p = random.choice(PREGUNTAS_TRIVIA)
    ops = p["ops"].copy(); random.shuffle(ops)
    nums = ["1️⃣","2️⃣","3️⃣","4️⃣"]
    desc = "\n".join(f"{nums[i]} {op.capitalize()}" for i, op in enumerate(ops))
    embed = discord.Embed(title="🃏 Trivia", description=f"**{p['p']}**\n\n{desc}", color=discord.Color.red())
    msg = await ctx.send(embed=embed)
    for emoji in nums[:len(ops)]: await msg.add_reaction(emoji)
    juegos_activos[ctx.channel.id] = True
    def check(r, u): return r.message.id == msg.id and not u.bot and str(r.emoji) in nums[:len(ops)]
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=20.0, check=check)
        elegida = ops[nums.index(str(reaction.emoji))]
        if elegida.lower() == p["r"].lower():
            await ctx.send(f"✅ ¡{user.mention} acertó! Era **{p['r'].capitalize()}** 🎉")
        else:
            await ctx.send(f"❌ {user.mention} falló. Era **{p['r'].capitalize()}**.")
    except asyncio.TimeoutError:
        await ctx.send(f"⌛ Tiempo. Era **{p['r'].capitalize()}**.")
    finally:
        juegos_activos.pop(ctx.channel.id, None)

@bot.command(name="adivina", aliases=["guess","numero"])
async def adivina_numero(ctx, maximo: int = 100):
    if ctx.channel.id in juegos_activos:
        return await ctx.send("❌ Ya hay un juego activo.")
    if not 5 <= maximo <= 1000:
        return await ctx.send("❌ Máximo entre 5 y 1000.")
    numero = random.randint(1, maximo)
    juegos_activos[ctx.channel.id] = True
    intentos = 0; max_intentos = 5
    embed = discord.Embed(title="🔢 Adivina el Número",
        description=f"Número entre **1 y {maximo}**. Tienes **{max_intentos} intentos**.", color=discord.Color.red())
    await ctx.send(embed=embed)
    def check(m): return m.channel == ctx.channel and not m.author.bot and m.content.isdigit()
    while intentos < max_intentos:
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            juegos_activos.pop(ctx.channel.id, None)
            return await ctx.send(f"⌛ Tiempo. Era **{numero}**.")
        intento = int(msg.content); intentos += 1; restantes = max_intentos - intentos
        if intento == numero:
            juegos_activos.pop(ctx.channel.id, None)
            return await ctx.send(f"🎉 ¡{msg.author.mention} acertó! Era **{numero}** en {intentos} intento(s)!")
        pista = "📈 **Mayor**." if intento < numero else "📉 **Menor**."
        if restantes > 0: await ctx.send(f"{pista} Quedan **{restantes}**.")
        else: await ctx.send(f"😢 Era **{numero}**.")
    juegos_activos.pop(ctx.channel.id, None)


# ═════════════════════════════════════════════════════════════
#  💬 FRASES DE PERSONAJES
# ═════════════════════════════════════════════════════════════

FRASES_PERSONAJES = {
    "naruto":["¡No voy a rendirme!","¡Cree en ti mismo!","¡Seré Hokage!","El dolor te hace más fuerte."],
    "goku":["¡Soy un Saiyan de la Tierra!","¡Kamehameha!","No puedo perder. Hay gente que me importa."],
    "luffy":["¡Seré el Rey de los Piratas!","¡Libertad!","¡Un hombre que no protege a sus amigos no vale nada!"],
    "zoro":["Nada me sucede hasta que yo digo que algo me sucede.","¡Nunca perderé de nuevo!","Solo hay un camino: adelante."],
    "eren":["Si no luchas, no puedes ganar.","La libertad es lo único que he querido."],
    "levi":["La única forma de encontrar la respuesta es elegir y no arrepentirte.","Tus camaradas confían en ti."],
    "light":["Soy el nuevo dios de este mundo.","El que gana tiene razón."],
    "itachi":["Eres débil porque te falta odio.","El perdón es la base de la paz.","Siempre seré tu hermano mayor."],
    "todoroki":["Uso mi poder como quiero.","No te debo nada."],
    "bakugo":["¡Ganaré y me convertiré en el número 1!","¡No necesito tu ayuda!"],
}

@bot.command(name="frase_personaje", aliases=["fp","anime_quote"])
async def frase_personaje(ctx, *, personaje: str = None):
    pers = list(FRASES_PERSONAJES.keys())
    if personaje is None: personaje = random.choice(pers)
    personaje = personaje.lower().strip()
    if personaje not in FRASES_PERSONAJES:
        return await ctx.send(f"❌ Disponibles: {', '.join(f'`{p}`' for p in pers)}")
    frase = random.choice(FRASES_PERSONAJES[personaje])
    colores = [discord.Color.red(), discord.Color.red(), discord.Color.red(), discord.Color.red(), discord.Color.red()]
    embed = discord.Embed(title=f"💬 {personaje.capitalize()}", description=f"*\"{frase}\"*", color=random.choice(colores))
    await ctx.send(embed=embed)

@bot.command(name="personajes_lista", aliases=["pl"])
async def personajes_lista(ctx):
    lista = ", ".join(f"`{p.capitalize()}`" for p in FRASES_PERSONAJES)
    embed = discord.Embed(title="💬 Personajes disponibles", description=lista, color=discord.Color.red())
    await ctx.send(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🔒 GESTIÓN DE CANALES (Admin)
# ═════════════════════════════════════════════════════════════

@bot.command(name="lock", aliases=["bloquear"])
@commands.check(es_admin)
async def lock(ctx, canal: discord.TextChannel = None, *, razon: str = "Sin razón"):
    canal = canal or ctx.channel
    ow = canal.overwrites_for(ctx.guild.default_role); ow.send_messages = False
    await canal.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"[{ctx.author}] {razon}")
    embed = discord.Embed(title="🔒 Canal Bloqueado", description=f"{canal.mention}\n📋 {razon}", color=discord.Color.red())
    await canal.send(embed=embed)
    if canal != ctx.channel: await ctx.send(f"✅ {canal.mention} bloqueado.")

@bot.command(name="unlock", aliases=["desbloquear"])
@commands.check(es_admin)
async def unlock(ctx, canal: discord.TextChannel = None, *, razon: str = "Sin razón"):
    canal = canal or ctx.channel
    ow = canal.overwrites_for(ctx.guild.default_role); ow.send_messages = None
    await canal.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"[{ctx.author}] {razon}")
    embed = discord.Embed(title="🔓 Canal Desbloqueado", description=f"{canal.mention}\n📋 {razon}", color=discord.Color.red())
    await canal.send(embed=embed)
    if canal != ctx.channel: await ctx.send(f"✅ {canal.mention} desbloqueado.")

@bot.command(name="lockall", aliases=["bloquear_todo"])
@commands.check(es_admin)
async def lockall(ctx, *, razon: str = "Sin razón"):
    msg = await ctx.send("⏳ Bloqueando todos los canales...")
    count = 0
    for c in ctx.guild.text_channels:
        try:
            ow = c.overwrites_for(ctx.guild.default_role); ow.send_messages = False
            await c.set_permissions(ctx.guild.default_role, overwrite=ow); count += 1
        except Exception: pass
    embed = discord.Embed(title="🔒 Servidor Bloqueado", description=f"**{count}** canales bloqueados.\n📋 {razon}", color=discord.Color.red())
    await msg.edit(content=None, embed=embed)

@bot.command(name="unlockall", aliases=["desbloquear_todo"])
@commands.check(es_admin)
async def unlockall(ctx, *, razon: str = "Sin razón"):
    msg = await ctx.send("⏳ Desbloqueando...")
    count = 0
    for c in ctx.guild.text_channels:
        try:
            ow = c.overwrites_for(ctx.guild.default_role); ow.send_messages = None
            await c.set_permissions(ctx.guild.default_role, overwrite=ow); count += 1
        except Exception: pass
    embed = discord.Embed(title="🔓 Servidor Desbloqueado", description=f"**{count}** canales.\n📋 {razon}", color=discord.Color.red())
    await msg.edit(content=None, embed=embed)

@bot.command(name="slowmode", aliases=["sm","modo_lento"])
@commands.check(es_admin)
async def slowmode(ctx, segundos: int = 0, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    if not 0 <= segundos <= 21600: return await ctx.send("❌ Entre 0 y 21600.")
    await canal.edit(slowmode_delay=segundos)
    if segundos == 0: await ctx.send(f"✅ Modo lento **off** en {canal.mention}.")
    else: await ctx.send(f"🐌 Modo lento {canal.mention}: **{segundos}s**.")

@bot.command(name="hide", aliases=["ocultar"])
@commands.check(es_admin)
async def hide(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    ow = canal.overwrites_for(ctx.guild.default_role); ow.view_channel = False
    await canal.set_permissions(ctx.guild.default_role, overwrite=ow)
    await ctx.send(f"👁️ {canal.mention} **oculto**.")

@bot.command(name="show", aliases=["mostrar"])
@commands.check(es_admin)
async def show(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    ow = canal.overwrites_for(ctx.guild.default_role); ow.view_channel = None
    await canal.set_permissions(ctx.guild.default_role, overwrite=ow)
    await ctx.send(f"👁️ {canal.mention} **visible**.")

@bot.command(name="topic", aliases=["tema"])
@commands.check(es_admin)
async def topic(ctx, *, texto: str):
    await ctx.channel.edit(topic=texto)
    await ctx.send(f"✅ Tema: **{texto}**")

@bot.command(name="rename_canal", aliases=["rc"])
@commands.check(es_admin)
async def rename_canal(ctx, *, nombre: str):
    nombre = nombre.lower().replace(" ", "-")
    viejo = ctx.channel.name
    await ctx.channel.edit(name=nombre)
    await ctx.send(f"✅ **#{viejo}** → **#{nombre}**")

@bot.command(name="crear_canal", aliases=["cc"])
@commands.check(es_admin)
async def crear_canal(ctx, *, nombre: str):
    nombre = nombre.lower().replace(" ", "-")
    c = await ctx.guild.create_text_channel(nombre, reason=f"Creado por {ctx.author}")
    await ctx.send(f"✅ Canal: {c.mention}")

@bot.command(name="eliminar_canal", aliases=["ec"])
@commands.check(es_admin)
async def eliminar_canal(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel; nombre = canal.name
    await canal.delete(reason=f"Eliminado por {ctx.author}")
    if canal != ctx.channel: await ctx.send(f"🗑️ **#{nombre}** eliminado.")

@bot.command(name="clonar_canal", aliases=["clone"])
@commands.check(es_admin)
async def clonar_canal(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    nuevo = await canal.clone(reason=f"Clonado por {ctx.author}")
    await ctx.send(f"✅ Clonado: {nuevo.mention}")

@bot.command(name="nsfw")
@commands.check(es_admin)
async def nsfw_toggle(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    nuevo = not canal.is_nsfw()
    await canal.edit(nsfw=nuevo)
    await ctx.send(f"NSFW **{'activado 🔞' if nuevo else 'desactivado ✅'}** en {canal.mention}.")


# ═════════════════════════════════════════════════════════════
#  🎭 GESTIÓN DE ROLES (Admin)
# ═════════════════════════════════════════════════════════════

@bot.command(name="dar_rol", aliases=["dr"])
@commands.check(es_admin)
async def dar_rol(ctx, member: discord.Member, *, nombre_rol: str):
    rol = discord.utils.get(ctx.guild.roles, name=nombre_rol)
    if not rol:
        nombre_lower = nombre_rol.lower()
        for r in ctx.guild.roles:
            if r.name.lower() == nombre_lower:
                rol = r
                break
    if not rol:
        similares = [r.name for r in ctx.guild.roles if nombre_rol.lower() in r.name.lower()][:5]
        msg = f"❌ No encontré el rol `{nombre_rol}`."
        if similares:
            msg += f"\n¿Quisiste decir? {', '.join(f'`{s}`' for s in similares)}"
        return await ctx.send(msg)
    if rol >= ctx.guild.me.top_role:
        return await ctx.send(f"❌ No puedo dar **{rol.name}** porque está por encima de mi rol en la jerarquía.")
    if rol in member.roles:
        return await ctx.send(f"⚠️ {member.mention} ya tiene **{rol.name}**.")
    try:
        await member.add_roles(rol, reason=f"Dado por {ctx.author}")
        embed = discord.Embed(title="✅ Rol Dado", color=rol.color)
        embed.add_field(name="👤 Usuario", value=member.mention, inline=True)
        embed.add_field(name="🎭 Rol",     value=rol.mention,    inline=True)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ Sin permisos para dar ese rol. Verifica la jerarquía del bot.")

@bot.command(name="quitar_rol", aliases=["qr"])
@commands.check(es_admin)
async def quitar_rol(ctx, member: discord.Member, *, nombre_rol: str):
    rol = discord.utils.get(ctx.guild.roles, name=nombre_rol)
    if not rol:
        for r in ctx.guild.roles:
            if r.name.lower() == nombre_rol.lower():
                rol = r; break
    if not rol:
        return await ctx.send(f"❌ No encontré `{nombre_rol}`.")
    if rol >= ctx.guild.me.top_role:
        return await ctx.send(f"❌ No puedo gestionar **{rol.name}** (jerarquía).")
    if rol not in member.roles:
        return await ctx.send(f"⚠️ {member.mention} no tiene **{rol.name}**.")
    try:
        await member.remove_roles(rol, reason=f"Quitado por {ctx.author}")
        embed = discord.Embed(title="✅ Rol Quitado", color=discord.Color.red())
        embed.add_field(name="👤 Usuario", value=member.mention, inline=True)
        embed.add_field(name="🎭 Rol",     value=rol.name,       inline=True)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ Sin permisos para quitar ese rol.")

@bot.command(name="crear_rol", aliases=["cr"])
@commands.check(es_admin)
async def crear_rol(ctx, color: str = "#99AAB5", *, nombre: str):
    try:
        color_obj = discord.Color.from_str(color)
    except Exception:
        return await ctx.send("❌ Color inválido. Usa `#RRGGBB`.")
    rol = await ctx.guild.create_role(name=nombre, color=color_obj, reason=f"Creado por {ctx.author}")
    await ctx.send(f"✅ Rol {rol.mention} creado.")

@bot.command(name="eliminar_rol", aliases=["er"])
@commands.check(es_admin)
async def eliminar_rol(ctx, *, nombre_rol: str):
    rol = discord.utils.get(ctx.guild.roles, name=nombre_rol)
    if not rol:
        for r in ctx.guild.roles:
            if r.name.lower() == nombre_rol.lower():
                rol = r; break
    if not rol: return await ctx.send(f"❌ Rol `{nombre_rol}` no encontrado.")
    try:
        await rol.delete(reason=f"Eliminado por {ctx.author}")
        await ctx.send(f"🗑️ **{nombre_rol}** eliminado.")
    except discord.Forbidden:
        await ctx.send("❌ Sin permisos.")

@bot.command(name="roles_usuario", aliases=["ru"])
async def roles_usuario(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]
    embed = discord.Embed(title=f"🎭 Roles de {member.display_name}", color=member.color)
    embed.description = " ".join(roles) if roles else "Sin roles"
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="listar_roles", aliases=["lroles"])
@commands.check(es_admin)
async def listar_roles(ctx):
    roles = [r for r in reversed(ctx.guild.roles) if r != ctx.guild.default_role]
    if not roles: return await ctx.send("❌ Sin roles.")
    paginas = []
    chunk = ""
    for r in roles:
        linea = f"{r.mention} — `{r.id}`\n"
        if len(chunk) + len(linea) > 900:
            paginas.append(chunk); chunk = ""
        chunk += linea
    if chunk: paginas.append(chunk)
    for i, p in enumerate(paginas, 1):
        embed = discord.Embed(title=f"🎭 Roles ({i}/{len(paginas)})", description=p, color=discord.Color.red())
        await ctx.send(embed=embed)

# ═══════════════════════════════════════════════════════════════
#  📢 SISTEMA DE ECHO / ANUNCIOS — Exagon Bot
# ═══════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
#  HELPER — construir embed de anuncio reutilizable
# ───────────────────────────────────────────────────────────────
def _build_anuncio_embed(
    titulo: str,
    mensaje: str,
    color: int = 0xFF0000,
    autor: discord.Member = None,
    imagen_url: str = None,
    thumbnail_url: str = None,
    footer_extra: str = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=titulo,
        description=mensaje,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    if autor:
        embed.set_author(name=autor.display_name, icon_url=autor.display_avatar.url)
    if imagen_url:
        embed.set_image(url=imagen_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if footer_extra:
        embed.set_footer(text=footer_extra)
    return embed


# ───────────────────────────────────────────────────────────────
#  !echo / /echo  —  El bot repite un mensaje (sin embed)
# ───────────────────────────────────────────────────────────────
@bot.command(name="echo", aliases=["say", "repeat"])
@commands.check(es_admin)
async def echo(ctx, canal: discord.TextChannel = None, *, mensaje: str):
    """El bot envía el mensaje indicado en el canal (sin embed).
    Uso: !echo [#canal] <mensaje>
    """
    destino = canal or ctx.channel
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await destino.send(mensaje)
    if destino != ctx.channel:
        await ctx.send(f"✅ Mensaje enviado en {destino.mention}.", delete_after=5)

@bot.tree.command(name="echo", description="📣 El bot repite un mensaje en el canal indicado")
@app_commands.describe(
    canal="Canal destino (opcional, por defecto el actual)",
    mensaje="Texto que enviará el bot"
)
@app_commands.checks.has_permissions(administrator=True)
async def echo_slash(
    interaction: discord.Interaction,
    mensaje: str,
    canal: discord.TextChannel = None
):
    destino = canal or interaction.channel
    await destino.send(mensaje)
    await interaction.response.send_message(
        f"✅ Mensaje enviado en {destino.mention}.", ephemeral=True
    )


# ───────────────────────────────────────────────────────────────
#  !anuncio / /anuncio  —  Anuncio con @everyone y embed rojo
# ───────────────────────────────────────────────────────────────
@bot.command(name="anuncio", aliases=["ann", "announce"])
@commands.check(es_admin)
async def anuncio(ctx, canal: discord.TextChannel = None, *, mensaje: str):
    """Envía un anuncio con @everyone y embed.
    Uso: !ann [#canal] <mensaje>
    """
    destino = canal or ctx.channel
    embed = _build_anuncio_embed(
        titulo="📢 Anuncio",
        mensaje=mensaje,
        color=0xFF0000,
        autor=ctx.author
    )
    await destino.send("@everyone", embed=embed)
    if destino != ctx.channel:
        await ctx.send(f"✅ Anuncio enviado en {destino.mention}.")

@bot.tree.command(name="anuncio", description="📢 Envía un anuncio con @everyone en el canal indicado")
@app_commands.describe(
    canal="Canal destino",
    mensaje="Texto del anuncio"
)
@app_commands.checks.has_permissions(administrator=True)
async def anuncio_slash(
    interaction: discord.Interaction,
    mensaje: str,
    canal: discord.TextChannel = None
):
    destino = canal or interaction.channel
    embed = _build_anuncio_embed(
        titulo="📢 Anuncio",
        mensaje=mensaje,
        color=0xFF0000,
        autor=interaction.user
    )
    await destino.send("@everyone", embed=embed)
    await interaction.response.send_message(
        f"✅ Anuncio enviado en {destino.mention}.", ephemeral=True
    )


# ───────────────────────────────────────────────────────────────
#  !emb / /emb  —  Embed personalizado con título y color
# ───────────────────────────────────────────────────────────────
@bot.command(name="embed_msg", aliases=["emb", "embed"])
@commands.check(es_admin)
async def embed_msg(
    ctx,
    canal: discord.TextChannel = None,
    titulo: str = "📌 Mensaje",
    color_hex: str = "FF0000",
    *,
    mensaje: str
):
    """Envía un embed con título y color personalizados.
    Uso: !emb [#canal] "Título" [ColorHex] <mensaje>
    Ejemplo: !emb #general "Reglas" 00FF00 Aquí van las reglas.
    """
    destino = canal or ctx.channel
    try:
        color = int(color_hex.strip("#"), 16)
    except ValueError:
        color = 0xFF0000
    embed = _build_anuncio_embed(
        titulo=titulo,
        mensaje=mensaje,
        color=color,
        autor=ctx.author
    )
    await destino.send(embed=embed)
    if destino != ctx.channel:
        await ctx.send(f"✅ Embed enviado en {destino.mention}.")

@bot.tree.command(name="embed", description="📌 Envía un embed personalizado con título y color")
@app_commands.describe(
    titulo="Título del embed",
    mensaje="Contenido del embed",
    color="Color en HEX sin # (ej: FF0000 para rojo)",
    canal="Canal destino (opcional)"
)
@app_commands.checks.has_permissions(administrator=True)
async def embed_slash(
    interaction: discord.Interaction,
    titulo: str,
    mensaje: str,
    color: str = "FF0000",
    canal: discord.TextChannel = None
):
    destino = canal or interaction.channel
    try:
        color_int = int(color.strip("#"), 16)
    except ValueError:
        color_int = 0xFF0000
    embed = _build_anuncio_embed(
        titulo=titulo,
        mensaje=mensaje,
        color=color_int,
        autor=interaction.user
    )
    await destino.send(embed=embed)
    await interaction.response.send_message(
        f"✅ Embed enviado en {destino.mention}.", ephemeral=True
    )


# ───────────────────────────────────────────────────────────────
#  !dm / /dm  —  Enviar DM privado a un usuario
# ───────────────────────────────────────────────────────────────
@bot.command(name="dm", aliases=["privado", "mensaje_privado"])
@commands.check(es_admin)
async def dm_cmd(ctx, member: discord.Member, *, mensaje: str):
    """Envía un DM a un usuario desde el bot.
    Uso: !dm @usuario <mensaje>
    """
    embed = discord.Embed(
        title=f"📩 Mensaje privado de {ctx.guild.name}",
        description=mensaje,
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Enviado por {ctx.author}")
    try:
        await member.send(embed=embed)
        await ctx.send(f"✅ DM enviado a {member.mention}.")
    except discord.Forbidden:
        await ctx.send(f"❌ No pude enviar DM a {member.mention} (tiene los DMs cerrados).")

@bot.tree.command(name="dm", description="📩 Envía un mensaje privado a un usuario")
@app_commands.describe(
    usuario="Usuario que recibirá el DM",
    mensaje="Contenido del DM"
)
@app_commands.checks.has_permissions(administrator=True)
async def dm_slash(
    interaction: discord.Interaction,
    usuario: discord.Member,
    mensaje: str
):
    embed = discord.Embed(
        title=f"📩 Mensaje privado de {interaction.guild.name}",
        description=mensaje,
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Enviado por {interaction.user}")
    try:
        await usuario.send(embed=embed)
        await interaction.response.send_message(
            f"✅ DM enviado a {usuario.mention}.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ No pude enviar DM a {usuario.mention} (DMs cerrados).", ephemeral=True
        )


# ───────────────────────────────────────────────────────────────
#  !dmrole / /dmrole  —  DM masivo a todos los usuarios con un rol
# ───────────────────────────────────────────────────────────────
@bot.command(name="dmrole", aliases=["massdm"])
@commands.check(es_admin)
async def dmrole(ctx, rol: discord.Role, *, mensaje: str):
    """Envía un DM a todos los miembros con un rol específico.
    Uso: !dmrole @Rol <mensaje>
    ⚠️ Úsalo con moderación para no ser marcado como spam.
    """
    miembros = [m for m in rol.members if not m.bot]
    if not miembros:
        return await ctx.send(f"❌ El rol {rol.mention} no tiene miembros (sin contar bots).")

    embed_prog = discord.Embed(
        title="⏳ Enviando DMs...",
        description=f"0/{len(miembros)} enviados",
        color=0xFF0000
    )
    msg = await ctx.send(embed=embed_prog)

    enviados, fallidos = 0, 0
    for member in miembros:
        dm_embed = discord.Embed(
            title=f"📩 Mensaje de {ctx.guild.name}",
            description=mensaje,
            color=0xFF0000,
            timestamp=datetime.now(timezone.utc)
        )
        dm_embed.set_footer(text=f"Enviado a miembros de: @{rol.name}")
        try:
            await member.send(embed=dm_embed)
            enviados += 1
        except discord.Forbidden:
            fallidos += 1
        await asyncio.sleep(1)   # Anti rate-limit

        if (enviados + fallidos) % 5 == 0:
            embed_prog.description = f"{enviados + fallidos}/{len(miembros)} enviados"
            await msg.edit(embed=embed_prog)

    embed_final = discord.Embed(title="✅ DMs Completados", color=0xFF0000)
    embed_final.add_field(name="✅ Enviados", value=str(enviados), inline=True)
    embed_final.add_field(name="❌ Fallidos", value=str(fallidos), inline=True)
    embed_final.add_field(name="👥 Rol",      value=rol.mention,  inline=True)
    await msg.edit(embed=embed_final)

@bot.tree.command(name="dmrole", description="📨 Envía un DM a todos los miembros con un rol")
@app_commands.describe(
    rol="Rol cuyos miembros recibirán el DM",
    mensaje="Mensaje a enviar"
)
@app_commands.checks.has_permissions(administrator=True)
async def dmrole_slash(interaction: discord.Interaction, rol: discord.Role, mensaje: str):
    await interaction.response.send_message(
        f"⏳ Enviando DMs a miembros de {rol.mention}...", ephemeral=True
    )
    miembros = [m for m in rol.members if not m.bot]
    enviados, fallidos = 0, 0
    for member in miembros:
        dm_embed = discord.Embed(
            title=f"📩 Mensaje de {interaction.guild.name}",
            description=mensaje,
            color=0xFF0000,
            timestamp=datetime.now(timezone.utc)
        )
        try:
            await member.send(embed=dm_embed)
            enviados += 1
        except discord.Forbidden:
            fallidos += 1
        await asyncio.sleep(1)
    await interaction.followup.send(
        f"✅ DMs enviados — ✅ {enviados} éxito · ❌ {fallidos} fallidos", ephemeral=True
    )


# ───────────────────────────────────────────────────────────────
#  !pin / !unpin  —  Pinear y despinear mensajes
# ───────────────────────────────────────────────────────────────
@bot.command(name="pin")
@commands.check(es_staff)
async def pin_cmd(ctx, message_id: int = None):
    """Pinea el mensaje indicado (o el último si no se da ID).
    Uso: !pin [ID_del_mensaje]
    """
    try:
        if message_id:
            msg = await ctx.channel.fetch_message(message_id)
        else:
            msgs = [m async for m in ctx.channel.history(limit=2)]
            msg = msgs[1] if len(msgs) > 1 else msgs[0]
        await msg.pin()
        await ctx.send(f"📌 Mensaje pineado por {ctx.author.mention}.", delete_after=5)
    except discord.NotFound:
        await ctx.send("❌ No encontré ese mensaje.")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos para pinear.")

@bot.command(name="unpin", aliases=["despin"])
@commands.check(es_staff)
async def unpin_cmd(ctx, message_id: int):
    """Despinea un mensaje por su ID.
    Uso: !unpin <ID_del_mensaje>
    """
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.unpin()
        await ctx.send(f"📌 Mensaje despineado por {ctx.author.mention}.", delete_after=5)
    except discord.NotFound:
        await ctx.send("❌ No encontré ese mensaje.")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos para despin.")

@bot.tree.command(name="pin", description="📌 Pinea un mensaje por su ID")
@app_commands.describe(message_id="ID del mensaje a pinear")
@app_commands.checks.has_permissions(manage_messages=True)
async def pin_slash(interaction: discord.Interaction, message_id: str):
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        await msg.pin()
        await interaction.response.send_message("📌 Mensaje pineado.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="unpin", description="📌 Despinea un mensaje por su ID")
@app_commands.describe(message_id="ID del mensaje a despin")
@app_commands.checks.has_permissions(manage_messages=True)
async def unpin_slash(interaction: discord.Interaction, message_id: str):
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        await msg.unpin()
        await interaction.response.send_message("📌 Mensaje despineado.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# ───────────────────────────────────────────────────────────────
#  !editembed / /editembed  —  Editar un embed ya enviado por el bot
# ───────────────────────────────────────────────────────────────
@bot.command(name="editembed", aliases=["editemb", "editarEmbed"])
@commands.check(es_admin)
async def editembed(ctx, message_id: int, *, nuevo_contenido: str):
    """Edita el contenido de un embed enviado por el bot.
    Uso: !editembed <ID_mensaje> <nuevo texto>
    """
    try:
        msg = await ctx.channel.fetch_message(message_id)
        if msg.author != bot.user:
            return await ctx.send("❌ Ese mensaje no es mío.")
        if not msg.embeds:
            return await ctx.send("❌ Ese mensaje no tiene embeds.")
        embed = msg.embeds[0]
        embed.description = nuevo_contenido
        embed.timestamp = datetime.now(timezone.utc)
        await msg.edit(embed=embed)
        await ctx.send("✅ Embed editado.", delete_after=5)
    except discord.NotFound:
        await ctx.send("❌ Mensaje no encontrado.")

@bot.tree.command(name="editembed", description="✏️ Edita el texto de un embed enviado por el bot")
@app_commands.describe(
    message_id="ID del mensaje con el embed",
    nuevo_contenido="Nuevo texto para el embed"
)
@app_commands.checks.has_permissions(administrator=True)
async def editembed_slash(interaction: discord.Interaction, message_id: str, nuevo_contenido: str):
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        if msg.author != bot.user or not msg.embeds:
            return await interaction.response.send_message("❌ No es un embed mío.", ephemeral=True)
        embed = msg.embeds[0]
        embed.description = nuevo_contenido
        embed.timestamp = datetime.now(timezone.utc)
        await msg.edit(embed=embed)
        await interaction.response.send_message("✅ Embed actualizado.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# ───────────────────────────────────────────────────────────────
#  !reglas / /reglas  —  Publicar embed de reglas del servidor
# ───────────────────────────────────────────────────────────────
@bot.command(name="reglas", aliases=["rules"])
@commands.check(es_admin)
async def reglas(ctx, canal: discord.TextChannel = None):
    """Envía el embed de reglas del servidor.
    Uso: !reglas [#canal]
    """
    destino = canal or ctx.channel
    embed = discord.Embed(
        title="📜 Reglas del Servidor",
        description=(
            "Por favor lee y respeta las siguientes reglas para mantener el orden de la comunidad."
        ),
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="1️⃣ Respeto",
        value="Traten a todos con respeto. No se tolerará el acoso ni el bullying.", inline=False)
    embed.add_field(name="2️⃣ Sin Spam",
        value="No envíes mensajes repetidos ni inunden los canales.", inline=False)
    embed.add_field(name="3️⃣ Sin NSFW",
        value="Contenido explícito solo en canales autorizados.", inline=False)
    embed.add_field(name="4️⃣ Sin Publicidad",
        value="No promociones otros servidores o productos sin autorización.", inline=False)
    embed.add_field(name="5️⃣ Sigue la TOS de Discord",
        value="Respeta los [Términos de Servicio](https://discord.com/terms) de Discord.", inline=False)
    embed.set_footer(text=f"{ctx.guild.name} • Al unirte aceptas estas reglas")
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    await destino.send(embed=embed)
    if destino != ctx.channel:
        await ctx.send(f"✅ Reglas enviadas en {destino.mention}.")

@bot.tree.command(name="reglas", description="📜 Publica el embed de reglas del servidor")
@app_commands.describe(canal="Canal donde publicar las reglas")
@app_commands.checks.has_permissions(administrator=True)
async def reglas_slash(interaction: discord.Interaction, canal: discord.TextChannel = None):
    destino = canal or interaction.channel
    embed = discord.Embed(
        title="📜 Reglas del Servidor",
        description="Por favor lee y respeta las siguientes reglas.",
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="1️⃣ Respeto",     value="Sin acoso ni bullying.",           inline=False)
    embed.add_field(name="2️⃣ Sin Spam",    value="No mensajes repetidos.",            inline=False)
    embed.add_field(name="3️⃣ Sin NSFW",    value="Solo en canales autorizados.",      inline=False)
    embed.add_field(name="4️⃣ Sin Publi",   value="Sin publicidad no autorizada.",      inline=False)
    embed.add_field(name="5️⃣ Discord TOS", value="Respeta los Términos de Discord.", inline=False)
    embed.set_footer(text=f"{interaction.guild.name} • Al unirte aceptas estas reglas")
    await destino.send(embed=embed)
    await interaction.response.send_message(f"✅ Reglas enviadas en {destino.mention}.", ephemeral=True)


# ───────────────────────────────────────────────────────────────
#  !bienvenida / /bienvenida  —  Enviar embed de bienvenida manual
# ───────────────────────────────────────────────────────────────
@bot.command(name="bienvenida", aliases=["welcome"])
@commands.check(es_staff)
async def bienvenida(ctx, member: discord.Member = None):
    """Da la bienvenida manual a un usuario con un embed.
    Uso: !bienvenida [@usuario]
    """
    member = member or ctx.author
    embed = discord.Embed(
        title=f"👋 ¡Bienvenido/a, {member.display_name}!",
        description=(
            f"Hola {member.mention}, ¡nos alegra tenerte en **{ctx.guild.name}**!\n\n"
            f"📜 Lee las reglas antes de participar.\n"
            f"🎭 Asigna tus roles en el canal correspondiente."
        ),
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Miembro #{ctx.guild.member_count}")
    await ctx.send(embed=embed)

@bot.tree.command(name="bienvenida", description="👋 Envía un embed de bienvenida a un usuario")
@app_commands.describe(usuario="Usuario a dar la bienvenida (opcional)")
@app_commands.checks.has_permissions(manage_messages=True)
async def bienvenida_slash(interaction: discord.Interaction, usuario: discord.Member = None):
    member = usuario or interaction.user
    embed = discord.Embed(
        title=f"👋 ¡Bienvenido/a, {member.display_name}!",
        description=(
            f"Hola {member.mention}, ¡nos alegra tenerte en **{interaction.guild.name}**!\n\n"
            f"📜 Lee las reglas antes de participar.\n"
            f"🎭 Asigna tus roles en el canal correspondiente."
        ),
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Miembro #{interaction.guild.member_count}")
    await interaction.response.send_message(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🔒 MODERACIÓN (Admin)
# ═════════════════════════════════════════════════════════════

@bot.command(name="ban")
@commands.check(es_admin)
async def ban_cmd(ctx, member: discord.Member, *, razon: str = "Sin razón"):
    if member == ctx.author: return await ctx.send("❌ No puedes banearte.")
    if member.guild_permissions.administrator: return await ctx.send("❌ No puedes banear a un admin.")
    try:
        await ctx.guild.ban(member, reason=f"[{ctx.author}] {razon}", delete_message_days=0)
    except discord.Forbidden: return await ctx.send("❌ Sin permisos.")
    embed = discord.Embed(title="🔨 Baneado", color=discord.Color.red())
    embed.add_field(name="👤 Usuario", value=f"{member} (`{member.id}`)", inline=True)
    embed.add_field(name="📋 Razón",   value=razon,            inline=True)
    embed.add_field(name="👮 Por",     value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="unban")
@commands.check(es_admin)
async def unban_cmd(ctx, *, usuario: str):
    bans = [entry async for entry in ctx.guild.bans()]
    objetivo = None
    for entry in bans:
        if str(entry.user.id) == usuario or str(entry.user) == usuario:
            objetivo = entry.user; break
    if not objetivo: return await ctx.send(f"❌ No encontré `{usuario}` en los bans.")
    await ctx.guild.unban(objetivo, reason=f"Desbaneado por {ctx.author}")
    embed = discord.Embed(title="✅ Desbaneado", color=discord.Color.red())
    embed.add_field(name="👤 Usuario", value=f"{objetivo} (`{objetivo.id}`)", inline=True)
    embed.add_field(name="👮 Por",     value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="kick")
@commands.check(es_admin)
async def kick_cmd(ctx, member: discord.Member, *, razon: str = "Sin razón"):
    if member == ctx.author: return await ctx.send("❌ No puedes kickearte.")
    try:
        await ctx.guild.kick(member, reason=f"[{ctx.author}] {razon}")
    except discord.Forbidden: return await ctx.send("❌ Sin permisos.")
    embed = discord.Embed(title="👢 Expulsado", color=discord.Color.red())
    embed.add_field(name="👤 Usuario", value=str(member),       inline=True)
    embed.add_field(name="📋 Razón",   value=razon,             inline=True)
    embed.add_field(name="👮 Por",     value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="mute")
@commands.check(es_admin)
async def mute_cmd(ctx, member: discord.Member, minutos: int = 10, *, razon: str = "Sin razón"):
    if not 1 <= minutos <= 40320: return await ctx.send("❌ Entre 1 y 40320 minutos.")
    import datetime as dt
    try:
        until = discord.utils.utcnow() + dt.timedelta(minutes=minutos)
        await member.timeout(until, reason=f"[{ctx.author}] {razon}")
    except discord.Forbidden: return await ctx.send("❌ Sin permisos.")
    embed = discord.Embed(title="🔇 Muteado", color=discord.Color.red())
    embed.add_field(name="👤 Usuario",   value=member.mention,     inline=True)
    embed.add_field(name="⏰ Duración",  value=f"{minutos} min",   inline=True)
    embed.add_field(name="📋 Razón",     value=razon,              inline=True)
    embed.add_field(name="👮 Por",       value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="unmute")
@commands.check(es_admin)
async def unmute_cmd(ctx, member: discord.Member):
    try: await member.timeout(None)
    except discord.Forbidden: return await ctx.send("❌ Sin permisos.")
    await ctx.send(f"✅ {member.mention} **desmuteado**.")

@bot.command(name="limpiar", aliases=["clear","purge"])
@commands.check(es_admin)
async def limpiar(ctx, cantidad: int = 10):
    if not 1 <= cantidad <= 100: return await ctx.send("❌ Entre 1 y 100.")
    borrados = await ctx.channel.purge(limit=cantidad + 1)
    msg = await ctx.send(f"🗑️ **{len(borrados)-1}** mensajes borrados.")
    await asyncio.sleep(3); await msg.delete()

@bot.command(name="limpiar_bots", aliases=["purgebots"])
@commands.check(es_admin)
async def limpiar_bots(ctx, cantidad: int = 50):
    def es_bot_msg(m): return m.author.bot
    borrados = await ctx.channel.purge(limit=cantidad, check=es_bot_msg)
    msg = await ctx.send(f"🤖 **{len(borrados)}** mensajes de bots borrados.")
    await asyncio.sleep(3); await msg.delete()

@bot.command(name="limpiar_usuario", aliases=["purgeuser"])
@commands.check(es_admin)
async def limpiar_usuario(ctx, member: discord.Member, cantidad: int = 50):
    def es_usuario(m): return m.author == member
    borrados = await ctx.channel.purge(limit=cantidad, check=es_usuario)
    msg = await ctx.send(f"🗑️ **{len(borrados)}** mensajes de {member.mention} borrados.")
    await asyncio.sleep(3); await msg.delete()

# [userinfo reemplazado por la interfaz ZyroX — ver más abajo]

@bot.command(name="serverinfo", aliases=["si","servidor"])
async def serverinfo(ctx):
    g = ctx.guild
    embed = discord.Embed(title=f"🏠 {g.name}", color=discord.Color.red())
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="🆔 ID",       value=g.id,              inline=True)
    embed.add_field(name="👑 Dueño",    value=g.owner.mention,   inline=True)
    embed.add_field(name="👥 Miembros", value=g.member_count,    inline=True)
    embed.add_field(name="💬 Canales",  value=len(g.channels),   inline=True)
    embed.add_field(name="🎭 Roles",    value=len(g.roles),      inline=True)
    embed.add_field(name="📅 Creado",   value=g.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📢 Nivel verificación", value=str(g.verification_level), inline=True)
    embed.add_field(name="💎 Boosts",   value=g.premium_subscription_count, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="nick", aliases=["apodo"])
@commands.check(es_admin)
async def nick(ctx, member: discord.Member, *, nuevo: str = None):
    try:
        viejo = member.display_name
        await member.edit(nick=nuevo)
        if nuevo:
            await ctx.send(f"✅ Nick de {member.mention}: **{viejo}** → **{nuevo}**")
        else:
            await ctx.send(f"✅ Nick de {member.mention} restablecido.")
    except discord.Forbidden:
        await ctx.send("❌ Sin permisos para cambiar ese nick.")

@bot.command(name="massnick")
@commands.check(es_admin)
async def massnick(ctx, *, nuevo: str):
    msg = await ctx.send(f"⏳ Cambiando nicks de **{ctx.guild.member_count}** miembros...")
    count = 0
    for m in ctx.guild.members:
        if not m.bot:
            try: await m.edit(nick=nuevo); count += 1
            except Exception: pass
    await msg.edit(content=f"✅ Nick cambiado a **{nuevo}** en **{count}** miembros.")


# ═════════════════════════════════════════════════════════════
#  🔒 COMANDO !v — DAR ROL ARN (Solo Admin)
# ═════════════════════════════════════════════════════════════

ROLES_POR_SERVIDOR = {
    1476763559982534829: {
        "dar":    1477556485092544532,
        "quitar": 1479630235283624049,
    },
    1473493322403414280: {
        "dar":    1473493514770972922,
        "quitar": None,
    },
    1480185559145250907: {
        "dar":    1473493514770972922,
        "quitar": None,
    },
}

class BuscarRolModal(discord.ui.Modal):
    def __init__(self, tipo: str, view):
        super().__init__(title=f"{'🟢 Rol a DAR' if tipo == 'dar' else '🔴 Rol a QUITAR'}")
        self.tipo = tipo
        self.parent_view = view
        self.input = discord.ui.TextInput(
            label="Nombre del rol (parcial o completo)",
            placeholder="Ej: Members, sin acceso, Admin...",
            required=True,
            max_length=100
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        buscar = self.input.value.lower().strip()

        if self.tipo == "quitar" and buscar in ("todos", "all", "todo"):
            self.parent_view.rol_quitar_id = "ALL"
            await interaction.response.send_message("🗑️ Se quitarán **TODOS** los roles.", ephemeral=True)
            return

        coincidencias = [
            r for r in guild.roles
            if buscar in r.name.lower()
            and r != guild.default_role
            and not r.managed
            and r < guild.me.top_role
        ]

        if not coincidencias:
            await interaction.response.send_message(
                f"❌ No encontré ningún rol con `{self.input.value}`. Intenta de nuevo.", ephemeral=True
            )
            return

        if len(coincidencias) == 1:
            rol = coincidencias[0]
            if self.tipo == "dar":
                self.parent_view.rol_dar_id = rol.id
                await interaction.response.send_message(f"🟢 Rol a dar: **{rol.name}**", ephemeral=True)
            else:
                self.parent_view.rol_quitar_id = rol.id
                await interaction.response.send_message(f"🔴 Rol a quitar: **{rol.name}**", ephemeral=True)
        else:
            opts = [
                discord.SelectOption(label=r.name[:100], value=str(r.id))
                for r in coincidencias[:25]
            ]
            view_sel = SeleccionarRolView(opts, self.tipo, self.parent_view)
            await interaction.response.send_message(
                f"🔍 Encontré **{len(coincidencias)}** roles. Selecciona uno:",
                view=view_sel,
                ephemeral=True
            )


class SeleccionarRolView(discord.ui.View):
    def __init__(self, opciones, tipo, parent_view):
        super().__init__(timeout=30)
        self.tipo        = tipo
        self.parent_view = parent_view
        sel = discord.ui.Select(placeholder="Selecciona el rol...", options=opciones)
        sel.callback = self.cb_sel
        self.add_item(sel)

    async def cb_sel(self, interaction: discord.Interaction):
        rol_id = int(interaction.data["values"][0])
        rol    = interaction.guild.get_role(rol_id)
        if self.tipo == "dar":
            self.parent_view.rol_dar_id = rol_id
            await interaction.response.send_message(f"🟢 Rol a dar: **{rol.name if rol else rol_id}**", ephemeral=True)
        else:
            self.parent_view.rol_quitar_id = rol_id
            await interaction.response.send_message(f"🔴 Rol a quitar: **{rol.name if rol else rol_id}**", ephemeral=True)
        self.stop()


class VerView(discord.ui.View):
    def __init__(self, ctx, member: discord.Member):
        super().__init__(timeout=60)
        self.ctx    = ctx
        self.member = member
        self.confirmado    = False
        self.rol_dar_id    = ROLES_POR_SERVIDOR.get(ctx.guild.id, {}).get("dar")
        self.rol_quitar_id = ROLES_POR_SERVIDOR.get(ctx.guild.id, {}).get("quitar", "ALL")
        if self.rol_quitar_id is None:
            self.rol_quitar_id = "ALL"

        btn_dar = discord.ui.Button(label="🟢 Cambiar rol a dar", style=discord.ButtonStyle.primary, row=0)
        btn_dar.callback = self.cb_abrir_dar
        self.add_item(btn_dar)

        btn_quitar = discord.ui.Button(label="🔴 Cambiar rol a quitar", style=discord.ButtonStyle.secondary, row=0)
        btn_quitar.callback = self.cb_abrir_quitar
        self.add_item(btn_quitar)

        btn_todos = discord.ui.Button(label="🗑️ Quitar todos los roles", style=discord.ButtonStyle.secondary, row=1)
        btn_todos.callback = self.cb_todos
        self.add_item(btn_todos)

        btn_ok = discord.ui.Button(label="✅ Confirmar", style=discord.ButtonStyle.success, row=2)
        btn_ok.callback = self.cb_confirmar
        self.add_item(btn_ok)

        btn_cancel = discord.ui.Button(label="❌ Cancelar", style=discord.ButtonStyle.danger, row=2)
        btn_cancel.callback = self.cb_cancelar
        self.add_item(btn_cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Solo quien ejecutó el comando puede usar esto.", ephemeral=True)
            return False
        return True

    async def cb_abrir_dar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BuscarRolModal("dar", self))

    async def cb_abrir_quitar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BuscarRolModal("quitar", self))

    async def cb_todos(self, interaction: discord.Interaction):
        self.rol_quitar_id = "ALL"
        await interaction.response.send_message("🗑️ Se quitarán **TODOS** los roles al confirmar.", ephemeral=True)

    async def cb_confirmar(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmado = True
        self.stop()

    async def cb_cancelar(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True)
        self.stop()


@bot.command(name="v")
@commands.check(es_admin)
async def dar_rol_arn(ctx, member: discord.Member):
    cfg_srv        = ROLES_POR_SERVIDOR.get(ctx.guild.id, {})
    dar_default    = cfg_srv.get("dar")
    quitar_default = cfg_srv.get("quitar")

    rol_dar_nombre    = ctx.guild.get_role(dar_default).name    if dar_default    and ctx.guild.get_role(dar_default)    else "Sin configurar"
    rol_quitar_nombre = ctx.guild.get_role(quitar_default).name if quitar_default and ctx.guild.get_role(quitar_default) else "Todos los roles"

    embed = discord.Embed(
        title="🔑 Dar Acceso — Configuración",
        description=(
            f"Configurando acceso para {member.mention}\n\n"
            f"🟢 **Cambiar rol a dar** — escribe el nombre del rol\n"
            f"🔴 **Cambiar rol a quitar** — escribe el nombre del rol\n"
            f"🗑️ **Quitar todos** — elimina todos los roles del usuario\n\n"
            f"O pulsa **✅ Confirmar** para usar los valores por defecto."
        ),
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Usuario",           value=member.mention,              inline=True)
    embed.add_field(name="🟢 Rol a dar",         value=f"**{rol_dar_nombre}**",     inline=True)
    embed.add_field(name="🔴 Rol(es) a quitar",  value=f"**{rol_quitar_nombre}**",  inline=True)

    view = VerView(ctx, member)
    msg  = await ctx.send(embed=embed, view=view)
    await view.wait()

    try:
        await msg.delete()
    except Exception:
        pass

    if not view.confirmado:
        return

    rol_dar_id    = view.rol_dar_id
    rol_quitar_id = view.rol_quitar_id

    if not rol_dar_id:
        return await ctx.send("❌ No hay rol configurado para dar. Selecciona uno en el menú.")

    rol_dar = ctx.guild.get_role(rol_dar_id)
    if not rol_dar:
        return await ctx.send("❌ No encontré el rol a dar.")

    roles_quitados = []
    roles_fallidos = []

    if rol_quitar_id == "ALL":
        roles_a_quitar = [
            r for r in member.roles
            if r != ctx.guild.default_role
            and not r.managed
            and r < ctx.guild.me.top_role
            and r.id != rol_dar.id
        ]
    else:
        r = ctx.guild.get_role(rol_quitar_id)
        roles_a_quitar = [r] if r and r in member.roles else []

    if roles_a_quitar:
        try:
            await member.remove_roles(*roles_a_quitar, reason=f"!v — {ctx.author}")
            roles_quitados = roles_a_quitar
        except discord.Forbidden:
            for r in roles_a_quitar:
                try:
                    await member.remove_roles(r, reason=f"!v — {ctx.author}")
                    roles_quitados.append(r)
                except discord.Forbidden:
                    roles_fallidos.append(r)

    try:
        await member.add_roles(rol_dar, reason=f"!v — acceso por {ctx.author}")
    except discord.Forbidden:
        return await ctx.send(f"❌ No pude asignar **{rol_dar.name}**. Sube el rol del bot en la jerarquía.")

    embed_ok = discord.Embed(title="✅ Acceso Concedido", color=discord.Color.red())
    embed_ok.set_thumbnail(url=member.display_avatar.url)
    embed_ok.add_field(name="👤 Miembro",   value=member.mention,        inline=True)
    embed_ok.add_field(name="✅ Rol dado",  value=f"**{rol_dar.name}**", inline=True)
    embed_ok.add_field(name="✍️ Por",        value=ctx.author.mention,    inline=True)
    if roles_quitados:
        embed_ok.add_field(
            name=f"🗑️ Roles quitados ({len(roles_quitados)})",
            value=", ".join(f"`{r.name}`" for r in roles_quitados),
            inline=False
        )
    if roles_fallidos:
        embed_ok.add_field(
            name="⚠️ No se pudieron quitar",
            value=", ".join(f"`{r.name}`" for r in roles_fallidos),
            inline=False
        )
    msg_ok = await ctx.send(embed=embed_ok)
    await asyncio.sleep(15)
    await msg_ok.delete()

@dar_rol_arn.error
async def dar_rol_arn_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Uso: `{PREFIX}v @usuario`")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Usuario no encontrado.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 Solo administradores.")


# ═════════════════════════════════════════════════════════════
#  ⚙️ CONFIGURACIÓN
# ═════════════════════════════════════════════════════════════

BOTCONFIG_FILE = "botconfig.json"

def cargar_botconfig() -> dict:
    if os.path.exists(BOTCONFIG_FILE):
        with open(BOTCONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"prefix": PREFIX}

def guardar_botconfig(cfg: dict):
    with open(BOTCONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

@bot.command(name="setprefix", aliases=["prefix","cambiar_prefijo"])
@commands.check(es_owner_o_admin)
async def setprefix(ctx, nuevo: str):
    if len(nuevo) > 3: return await ctx.send("❌ Máx 3 caracteres.")
    viejo = bot.command_prefix
    cfg = cargar_botconfig(); cfg["prefix"] = nuevo; guardar_botconfig(cfg)
    bot.command_prefix = nuevo
    await ctx.send(f"✅ Prefijo: `{viejo}` → `{nuevo}`")


# ═════════════════════════════════════════════════════════════
#  🌐 COMANDOS GENERALES
# ═════════════════════════════════════════════════════════════

@bot.command(name="ping")
async def ping(ctx):
    lat = round(bot.latency * 1000)
    color = discord.Color.red() if lat < 100 else discord.Color.red() if lat < 200 else discord.Color.red()
    await ctx.send(embed=discord.Embed(title="🏓 Pong!", description=f"**{lat}ms**", color=color))

@bot.command(name="avatar", aliases=["av","foto"])
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ {member.display_name}", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    embed.add_field(name="🔗 Link", value=f"[Descargar]({member.display_avatar.url})", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="banner")
async def banner(ctx, member: discord.Member = None):
    member = member or ctx.author
    user = await bot.fetch_user(member.id)
    if not user.banner: return await ctx.send(f"❌ {member.display_name} no tiene banner.")
    embed = discord.Embed(title=f"🖼️ Banner de {member.display_name}", color=member.color)
    embed.set_image(url=user.banner.url)
    await ctx.send(embed=embed)

@bot.command(name="stats", aliases=["estadisticas"])
async def stats(ctx):
    g = ctx.guild
    total   = g.member_count
    bots    = sum(1 for m in g.members if m.bot)
    humanos = total - bots
    en_linea = sum(1 for m in g.members if m.status != discord.Status.offline and not m.bot)
    embed = discord.Embed(title=f"📊 {g.name}", color=discord.Color.red())
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="👥 Total",    value=total,    inline=True)
    embed.add_field(name="🧑 Humanos",  value=humanos,  inline=True)
    embed.add_field(name="🤖 Bots",     value=bots,     inline=True)
    embed.add_field(name="🟢 En línea", value=en_linea, inline=True)
    embed.add_field(name="💬 Canales",  value=len(g.text_channels),  inline=True)
    embed.add_field(name="🔊 Voz",      value=len(g.voice_channels), inline=True)
    embed.add_field(name="🎭 Roles",    value=len(g.roles),  inline=True)
    embed.add_field(name="😄 Emojis",   value=len(g.emojis), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="botinfo", aliases=["bot_info"])
async def botinfo(ctx):
    import platform
    embed = discord.Embed(title="🤖 Info del Bot", color=discord.Color.red())
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(name="🏷️ Nombre",    value=str(bot.user),           inline=True)
    embed.add_field(name="🆔 ID",        value=bot.user.id,             inline=True)
    embed.add_field(name="🖥️ Python",    value=platform.python_version(), inline=True)
    embed.add_field(name="📚 discord.py",value=discord.__version__,     inline=True)
    embed.add_field(name="🏠 Servidores",value=len(bot.guilds),         inline=True)
    embed.add_field(name="👥 Usuarios",  value=len(bot.users),          inline=True)
    embed.add_field(name="📜 Comandos",  value=len(bot.commands),       inline=True)
    embed.add_field(name="⚙️ Prefijo",   value=f"`{bot.command_prefix}`",inline=True)
    await ctx.send(embed=embed)

@bot.command(name="invitar", aliases=["invite"])
async def invitar(ctx):
    url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot"
    embed = discord.Embed(title="🔗 Invitar", description=f"[Clic aquí]({url})", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="clima", aliases=["weather","tiempo"])
async def clima(ctx, *, ciudad: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://wttr.in/{ciudad.replace(' ','+')}?format=j1") as resp:
                if resp.status != 200: return await ctx.send("❌ Ciudad no encontrada.")
                data    = await resp.json()
                actual  = data["current_condition"][0]
                embed   = discord.Embed(title=f"🌤️ {ciudad.title()}", color=discord.Color.red())
                embed.add_field(name="🌡️ Temp",      value=f"{actual['temp_C']}°C",       inline=True)
                embed.add_field(name="🤔 Sensación", value=f"{actual['FeelsLikeC']}°C",   inline=True)
                embed.add_field(name="💧 Humedad",   value=f"{actual['humidity']}%",       inline=True)
                embed.add_field(name="💨 Viento",    value=f"{actual['windspeedKmph']} km/h", inline=True)
                embed.add_field(name="☁️ Estado",    value=actual['weatherDesc'][0]['value'], inline=True)
                await ctx.send(embed=embed)
    except Exception: await ctx.send("❌ No pude obtener el clima.")

@bot.command(name="traducir", aliases=["translate","tr"])
async def traducir(ctx, idioma: str, *, texto: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mymemory.translated.net/get?q={texto}&langpair=es|{idioma}") as resp:
                data = await resp.json()
                trad = data["responseData"]["translatedText"]
                embed = discord.Embed(title="🌍 Traducción", color=discord.Color.red())
                embed.add_field(name="📝 Original",  value=texto, inline=False)
                embed.add_field(name="✅ Traducido", value=trad,  inline=False)
                embed.add_field(name="🌐 Idioma",    value=idioma, inline=True)
                await ctx.send(embed=embed)
    except Exception: await ctx.send("❌ No pude traducir.")

@bot.command(name="calcular", aliases=["calc","matematica"])
async def calcular(ctx, *, expresion: str):
    try:
        if not all(c in "0123456789+-*/.() " for c in expresion):
            return await ctx.send("❌ Solo `+ - * / ( )`.")
        resultado = eval(expresion)
        embed = discord.Embed(title="🧮 Calculadora", color=discord.Color.red())
        embed.add_field(name="📝", value=f"`{expresion}`",  inline=False)
        embed.add_field(name="✅", value=f"**{resultado}**", inline=False)
        await ctx.send(embed=embed)
    except ZeroDivisionError: await ctx.send("❌ División entre cero.")
    except Exception: await ctx.send("❌ Expresión inválida.")

@bot.command(name="color")
async def color_cmd(ctx, *, hex_color: str):
    hex_color = hex_color.strip("#")
    try:
        r = int(hex_color[0:2], 16); g = int(hex_color[2:4], 16); b = int(hex_color[4:6], 16)
    except Exception: return await ctx.send("❌ Usa `!color FF0000`")
    embed = discord.Embed(title=f"🎨 #{hex_color.upper()}", color=int(hex_color, 16))
    embed.add_field(name="R", value=r, inline=True)
    embed.add_field(name="G", value=g, inline=True)
    embed.add_field(name="B", value=b, inline=True)
    embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{hex_color}/100x100")
    await ctx.send(embed=embed)

@bot.command(name="sugerencia", aliases=["suggest"])
async def sugerencia(ctx, canal: discord.TextChannel = None, *, texto: str):
    canal = canal or ctx.channel
    embed = discord.Embed(title="💡 Sugerencia", description=texto, color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    msg = await canal.send(embed=embed)
    await msg.add_reaction("✅"); await msg.add_reaction("❌")
    if canal != ctx.channel: await ctx.send(f"✅ Enviada en {canal.mention}.")

@bot.command(name="reporte", aliases=["report"])
async def reporte(ctx, member: discord.Member, *, razon: str):
    if member == ctx.author: return await ctx.send("❌ No puedes reportarte.")
    embed = discord.Embed(title="🚨 Reporte", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
    embed.add_field(name="👤 Reportado",     value=f"{member.mention} (`{member.id}`)", inline=False)
    embed.add_field(name="📋 Razón",         value=razon,              inline=False)
    embed.add_field(name="📩 Por",           value=ctx.author.mention, inline=False)
    embed.add_field(name="📍 Canal",         value=ctx.channel.mention, inline=False)
    cfg = cargar_antinuke(ctx.guild.id)
    log_ch_id = cfg.get("log_channel")
    canal_destino = ctx.guild.get_channel(int(log_ch_id)) if log_ch_id else ctx.channel
    await canal_destino.send(embed=embed)
    try: await ctx.message.delete()
    except Exception: pass
    try: await ctx.author.send(f"✅ Reporte sobre **{member.display_name}** enviado.")
    except Exception: pass

@bot.command(name="dado_personalizado", aliases=["dp"])
async def dado_personalizado(ctx, cantidad: int = 1, lados: int = 6):
    if not 1 <= cantidad <= 20: return await ctx.send("❌ Entre 1 y 20 dados.")
    if not 2 <= lados <= 1000: return await ctx.send("❌ Entre 2 y 1000 lados.")
    resultados = [random.randint(1, lados) for _ in range(cantidad)]
    total = sum(resultados)
    embed = discord.Embed(title=f"🎲 {cantidad}d{lados}", color=discord.Color.red())
    embed.add_field(name="Resultados", value=" + ".join(f"`{r}`" for r in resultados), inline=False)
    embed.add_field(name="Total", value=f"**{total}**", inline=True)
    if cantidad > 1: embed.add_field(name="Promedio", value=f"**{total/cantidad:.1f}**", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="recordar", aliases=["remind","reminder"])
async def recordar(ctx, tiempo: str, *, mensaje: str):
    unidades = {"s":1,"m":60,"h":3600}
    try:
        unidad = tiempo[-1].lower(); cantidad = int(tiempo[:-1])
        if unidad not in unidades or not 1 <= cantidad <= 86400: raise ValueError
    except Exception: return await ctx.send("❌ Ej: `!recordar 10m mensaje` (s/m/h)")
    segundos = cantidad * unidades[unidad]
    nombres  = {"s":"segundo(s)","m":"minuto(s)","h":"hora(s)"}
    await ctx.send(f"⏰ Te recordaré en **{cantidad} {nombres[unidad]}**.")
    await asyncio.sleep(segundos)
    try:
        embed = discord.Embed(title="⏰ Recordatorio", description=mensaje, color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        await ctx.author.send(embed=embed)
    except Exception: pass
    await ctx.send(f"⏰ {ctx.author.mention} ¡Recordatorio! **{mensaje}**")


# ═════════════════════════════════════════════════════════════
#  🎂 CUMPLEAÑOS
# ═════════════════════════════════════════════════════════════

CUMPLE_FILE = "cumpleanos.json"

def cargar_cumples() -> dict:
    if os.path.exists(CUMPLE_FILE):
        with open(CUMPLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_cumples(data: dict):
    with open(CUMPLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@bot.command(name="cumple", aliases=["birthday"])
async def cumple(ctx, fecha: str = None):
    if fecha is None:
        cumples = cargar_cumples(); uid = str(ctx.author.id)
        if uid in cumples: return await ctx.send(f"🎂 Tu cumpleaños: **{cumples[uid]}**.")
        return await ctx.send("❌ No tienes cumpleaños. Usa `!cumple DD/MM`.")
    try:
        dia, mes = map(int, fecha.split("/"))
        if not (1 <= dia <= 31 and 1 <= mes <= 12): raise ValueError
    except Exception: return await ctx.send("❌ Usa `DD/MM`. Ej: `!cumple 25/12`")
    cumples = cargar_cumples()
    cumples[str(ctx.author.id)] = f"{dia:02d}/{mes:02d}"
    guardar_cumples(cumples)
    await ctx.send(f"🎂 Registrado: **{dia:02d}/{mes:02d}**")

@bot.command(name="cumple_ver", aliases=["ver_cumple"])
async def cumple_ver(ctx, member: discord.Member = None):
    member = member or ctx.author
    cumples = cargar_cumples(); uid = str(member.id)
    if uid not in cumples: return await ctx.send(f"❌ {member.display_name} sin cumpleaños.")
    fecha = cumples[uid]; dia, mes = map(int, fecha.split("/"))
    hoy = datetime.now(timezone.utc)
    este = datetime(hoy.year, mes, dia, tzinfo=timezone.utc)
    if este < hoy: este = datetime(hoy.year + 1, mes, dia, tzinfo=timezone.utc)
    dias = (este - hoy).days
    embed = discord.Embed(title=f"🎂 {member.display_name}", color=discord.Color.red())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="📅 Fecha", value=fecha, inline=True)
    embed.add_field(name="⏰ Faltan", value=f"**{dias}** días", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="cumples_lista", aliases=["lista_cumples"])
async def cumples_lista(ctx):
    cumples = cargar_cumples()
    if not cumples: return await ctx.send("❌ Nadie ha registrado cumpleaños.")
    hoy = datetime.now(timezone.utc); lista = []
    for uid, fecha in cumples.items():
        try:
            dia, mes = map(int, fecha.split("/"))
            este = datetime(hoy.year, mes, dia, tzinfo=timezone.utc)
            if este < hoy: este = datetime(hoy.year + 1, mes, dia, tzinfo=timezone.utc)
            lista.append(((este - hoy).days, uid, fecha))
        except Exception: pass
    lista.sort()
    embed = discord.Embed(title="🎂 Próximos Cumpleaños", color=discord.Color.red())
    for dias, uid, fecha in lista[:10]:
        member = ctx.guild.get_member(int(uid))
        nombre = member.display_name if member else f"<@{uid}>"
        embed.add_field(name=f"🎉 {nombre}", value=f"**{fecha}** — en {dias} días", inline=False)
    await ctx.send(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🎰 JUEGOS
# ═════════════════════════════════════════════════════════════

@bot.command(name="dado", aliases=["dice","d6"])
async def dado(ctx, lados: int = 6):
    if not 2 <= lados <= 100: return await ctx.send("❌ Entre 2 y 100.")
    resultado = random.randint(1, lados)
    embed = discord.Embed(title="🎲 Dado", color=discord.Color.red())
    embed.add_field(name=f"D{lados}", value=f"**{resultado}**", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="moneda", aliases=["coin","flip"])
async def moneda(ctx):
    resultado = random.choice(["🪙 Cara", "🪙 Sello"])
    embed = discord.Embed(title="🪙 Moneda", description=f"**{resultado}**", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="ruleta", aliases=["roulette"])
async def ruleta(ctx, *opciones):
    if len(opciones) < 2: return await ctx.send("❌ Al menos 2 opciones.")
    elegida = random.choice(opciones)
    embed = discord.Embed(title="🎡 Ruleta", color=discord.Color.red())
    embed.add_field(name="Opciones", value=" | ".join(f"`{o}`" for o in opciones), inline=False)
    embed.add_field(name="🏆 Elegida", value=f"**{elegida}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="8ball", aliases=["bola8"])
async def bola_ocho(ctx, *, pregunta: str):
    respuestas = [
        "✅ Sí, definitivamente.","✅ Todo indica que sí.","✅ Sin duda.",
        "🤔 No está claro.","🤔 Concéntrate y pregunta de nuevo.",
        "❌ No cuentes con ello.","❌ Mi respuesta es no.","❌ Definitivamente no."
    ]
    embed = discord.Embed(title="🎱 Bola Mágica", color=discord.Color.red())
    embed.add_field(name="❓ Pregunta", value=pregunta, inline=False)
    embed.add_field(name="🔮 Respuesta", value=random.choice(respuestas), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="piedra", aliases=["rps"])
async def piedra_papel_tijera(ctx, eleccion: str):
    opciones = ["piedra","papel","tijera"]
    eleccion = eleccion.lower()
    if eleccion not in opciones: return await ctx.send("❌ `piedra`, `papel` o `tijera`")
    bot_eleccion = random.choice(opciones)
    emojis = {"piedra":"🪨","papel":"📄","tijera":"✂️"}
    if eleccion == bot_eleccion: resultado = "🤝 Empate"; color = discord.Color.red()
    elif (eleccion=="piedra" and bot_eleccion=="tijera") or \
         (eleccion=="papel"  and bot_eleccion=="piedra") or \
         (eleccion=="tijera" and bot_eleccion=="papel"):
        resultado = "🏆 ¡Ganaste!"; color = discord.Color.red()
    else: resultado = "😈 ¡Perdiste!"; color = discord.Color.red()
    embed = discord.Embed(title="🎮 RPS", description=resultado, color=color)
    embed.add_field(name="Tú",  value=emojis[eleccion],     inline=True)
    embed.add_field(name="Bot", value=emojis[bot_eleccion], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="verdad_o_reto", aliases=["tor","verdad","reto"])
async def verdad_o_reto(ctx, member: discord.Member = None):
    member = member or ctx.author
    verdades = [
        "¿Cuál es tu mayor miedo?","¿Qué es lo más embarazoso que te ha pasado?",
        "¿Tienes algún crush aquí?","¿Cuál es tu secreto más oscuro?",
        "¿A quién de aquí considerarías como pareja?","¿Cuál es tu mayor defecto?",
    ]
    retos = [
        "Cambia tu nick a 'Pollo Frito' por 1 hora.",
        "Manda un meme al canal principal.",
        "Di algo positivo sobre cada persona en el canal de voz.",
        "Escribe un poema sobre el bot.",
        "Di 'yo amo a mi bot' 3 veces en el chat.",
        "Manda una foto de tu escritorio/pantalla.",
    ]
    tipo = random.choice(["Verdad 🔮", "Reto 💥"])
    contenido = random.choice(verdades) if "Verdad" in tipo else random.choice(retos)
    color = discord.Color.red() if "Verdad" in tipo else discord.Color.red()
    embed = discord.Embed(title=f"🎮 {tipo}", description=f"Para {member.mention}\n\n**{contenido}**", color=color)
    await ctx.send(embed=embed)

@bot.command(name="acertijo", aliases=["riddle"])
async def acertijo(ctx):
    acertijos = [
        ("Tengo ciudades, pero no hay casas. Tengo montañas, pero no hay árboles. Tengo agua, pero no hay peces. ¿Qué soy?", "Un mapa"),
        ("Cuanto más me seques, más mojado te quedas. ¿Qué soy?", "Una toalla"),
        ("Tengo manos pero no puedo aplaudir. ¿Qué soy?", "Un reloj"),
        ("Soy ligero como una pluma, pero ni el hombre más fuerte puede sostenerme más de unos minutos. ¿Qué soy?", "El aliento"),
        ("Tengo un corazón que no late, tengo una boca que no habla. ¿Qué soy?", "Una alcachofa"),
        ("Siempre delante de ti, pero no se puede ver. ¿Qué soy?", "El futuro"),
    ]
    pregunta, respuesta = random.choice(acertijos)
    embed = discord.Embed(title="🧩 Acertijo", description=pregunta, color=discord.Color.red())
    await ctx.send(embed=embed)

    def check(m): return m.channel == ctx.channel and not m.author.bot
    try:
        msg_r = await bot.wait_for("message", timeout=30.0, check=check)
        if respuesta.lower() in msg_r.content.lower():
            await ctx.send(f"✅ ¡{msg_r.author.mention} acertó! Era **{respuesta}** 🎉")
        else:
            await ctx.send(f"❌ Era **{respuesta}**.")
    except asyncio.TimeoutError:
        await ctx.send(f"⌛ Tiempo. Era **{respuesta}**.")


# ═════════════════════════════════════════════════════════════
#  😂 MEMES Y FRASES
# ═════════════════════════════════════════════════════════════

FRASES_MOTIVACION = [
    "El éxito no es definitivo, el fracaso no es fatal. — Churchill",
    "El único modo de hacer un gran trabajo es amar lo que haces. — Jobs",
    "La vida es 10% lo que te sucede y 90% cómo reaccionas. — Swindoll",
    "El futuro pertenece a quienes creen en la belleza de sus sueños. — Roosevelt",
    "Sé el cambio que quieres ver en el mundo. — Gandhi",
    "No esperes oportunidades extraordinarias. Aprovecha las ordinarias.",
    "Cree en ti mismo y todo lo demás vendrá solo.",
]

CHISTES = [
    "¿Por qué los pájaros vuelan al sur? Porque caminar es muy lejos 🐦",
    "¿Qué le dijo el 0 al 8? Bonito cinturón 😂",
    "¿Por qué el libro de matemáticas estaba triste? Porque tenía muchos problemas 📚",
    "¿Qué hace una abeja en el gimnasio? ¡Zum-ba! 🐝",
    "¿Por qué los esqueletos no pelean? No tienen agallas 💀",
]

@bot.command(name="frase", aliases=["motivacion","quote"])
async def frase_random(ctx):
    embed = discord.Embed(title="💬 Frase del día", description=f"*{random.choice(FRASES_MOTIVACION)}*", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="chiste", aliases=["joke"])
async def chiste_random(ctx):
    embed = discord.Embed(title="😂 Chiste", description=random.choice(CHISTES), color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="meme")
async def meme_random(ctx):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=data["title"], color=discord.Color.red())
                    embed.set_image(url=data["url"])
                    await ctx.send(embed=embed)
                    return
    except Exception: pass
    await ctx.send("❌ No pude obtener un meme. Intenta más tarde.")

@bot.command(name="rng", aliases=["random","aleatorio"])
async def rng(ctx, minimo: int = 1, maximo: int = 100):
    if minimo >= maximo: return await ctx.send("❌ El mínimo debe ser menor que el máximo.")
    resultado = random.randint(minimo, maximo)
    embed = discord.Embed(title="🎲 Número Aleatorio", color=discord.Color.red())
    embed.add_field(name="Rango", value=f"`{minimo}` – `{maximo}`", inline=True)
    embed.add_field(name="Resultado", value=f"**{resultado}**", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="buscar", aliases=["google","search"])
async def buscar(ctx, *, termino: str):
    url = f"https://www.google.com/search?q={termino.replace(' ', '+')}"
    embed = discord.Embed(title=f"🔍 Buscar: {termino}", description=f"[Haz clic para buscar en Google]({url})", color=discord.Color.red())
    await ctx.send(embed=embed)


# ═════════════════════════════════════════════════════════════
#  🎁 SORTEOS Y ENCUESTAS
# ═════════════════════════════════════════════════════════════

@bot.command(name="sorteo", aliases=["giveaway"])
@commands.check(es_staff)
async def sorteo(ctx, segundos: int, *, premio: str):
    if not 10 <= segundos <= 86400: return await ctx.send("❌ Entre 10s y 24h.")
    embed = discord.Embed(title="🎁 ¡SORTEO!",
        description=f"**Premio:** {premio}\nReacciona con 🎉\n⏰ **{segundos}s**",
        color=discord.Color.red())
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(segundos)
    msg = await ctx.channel.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    participantes = [u async for u in reaction.users() if not u.bot]
    if not participantes:
        embed_fin = discord.Embed(title="🎁 Sin participantes 😢", color=discord.Color.red())
    else:
        ganador = random.choice(participantes)
        embed_fin = discord.Embed(title="🎉 ¡Ganador!",
            description=f"**Premio:** {premio}\n🏆 {ganador.mention}", color=discord.Color.red())
    await ctx.send(embed=embed_fin)

@bot.command(name="encuesta", aliases=["poll"])
async def encuesta(ctx, *, texto: str):
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) < 2: return await ctx.send("❌ Formato: `!encuesta ¿Pregunta? | op1 | op2`")
    pregunta = partes[0]; opciones = partes[1:]
    if len(opciones) > 9: return await ctx.send("❌ Máximo 9 opciones.")
    nums = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    desc = "\n".join(f"{nums[i]} {op}" for i, op in enumerate(opciones))
    embed = discord.Embed(title=f"📊 {pregunta}", description=desc, color=discord.Color.red())
    msg = await ctx.send(embed=embed)
    for i in range(len(opciones)): await msg.add_reaction(nums[i])

@bot.command(name="encuesta_si_no", aliases=["yesno"])
async def encuesta_si_no(ctx, *, pregunta: str):
    embed = discord.Embed(title=f"📊 {pregunta}", color=discord.Color.red())
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅"); await msg.add_reaction("❌")


# ═════════════════════════════════════════════════════════════
#  🐱 ANIME
# ═════════════════════════════════════════════════════════════

ANIME_ACCIONES = {
    "abrazar":  {"emoji":"🤗","gif_tag":"hug",   "msg":"{a} abraza a {b} 🤗",             "boton":"Abrazar devuelta 🤗"},
    "pat":      {"emoji":"👋","gif_tag":"pat",    "msg":"{a} le da palmaditas a {b} 👋",   "boton":"Palmaditas 👋"},
    "slap":     {"emoji":"😤","gif_tag":"slap",   "msg":"{a} cachetea a {b} 😤",           "boton":"Devolver 😤"},
    "kiss":     {"emoji":"💋","gif_tag":"kiss",   "msg":"{a} besa a {b} 💋",              "boton":"Beso 💋"},
    "cry":      {"emoji":"😢","gif_tag":"cry",    "msg":"{a} está llorando 😢",            "boton":"Consolar 🫂"},
    "poke":     {"emoji":"👉","gif_tag":"poke",   "msg":"{a} toca a {b} 👉",              "boton":"Devolver 👉"},
    "cuddle":   {"emoji":"🥰","gif_tag":"cuddle", "msg":"{a} acurruca a {b} 🥰",          "boton":"Acurrucarse 🥰"},
    "bite":     {"emoji":"😬","gif_tag":"bite",   "msg":"{a} muerde a {b} 😬",            "boton":"Morder 😬"},
    "wave":     {"emoji":"👋","gif_tag":"wave",   "msg":"{a} saluda a {b} 👋",            "boton":"Saludar 👋"},
    "dance":    {"emoji":"💃","gif_tag":"dance",  "msg":"{a} baila con {b} 💃",           "boton":"Bailar 💃"},
}

_contadores_anime = {}

def get_contador(uid1: int, uid2: int, accion: str) -> int:
    key = f"{min(uid1,uid2)}-{max(uid1,uid2)}-{accion}"
    _contadores_anime[key] = _contadores_anime.get(key, 0) + 1
    return _contadores_anime[key]

async def obtener_gif_anime(tag: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://nekos.best/api/v2/{tag}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["results"][0]["url"]
    except Exception: pass
    return None

class AnimeView(discord.ui.View):
    def __init__(self, autor, target, accion, info):
        super().__init__(timeout=60)
        self.autor = autor; self.target = target; self.accion = accion; self.info = info
        btn_r = discord.ui.Button(label=info["boton"], style=discord.ButtonStyle.primary)
        btn_x = discord.ui.Button(label="Rechazar ✖", style=discord.ButtonStyle.danger)
        async def r_cb(interaction):
            if interaction.user.id != self.target.id:
                return await interaction.response.send_message("❌ No es para ti.", ephemeral=True)
            count = get_contador(self.autor.id, self.target.id, self.accion)
            gif   = await obtener_gif_anime(self.info["gif_tag"])
            msg   = self.info["msg"].format(a=self.target.display_name, b=self.autor.display_name)
            embed = discord.Embed(description=msg, color=discord.Color.red())
            if gif: embed.set_image(url=gif)
            await interaction.response.send_message(embed=embed); self.stop()
        async def x_cb(interaction):
            if interaction.user.id != self.target.id:
                return await interaction.response.send_message("❌ No es para ti.", ephemeral=True)
            await interaction.response.send_message(f"💔 **{self.target.display_name}** rechazó a **{self.autor.display_name}**.")
            self.stop()
        btn_r.callback = r_cb; btn_x.callback = x_cb
        self.add_item(btn_r); self.add_item(btn_x)

def make_anime_cmd(accion, info):
    @bot.command(name=accion)
    async def _cmd(ctx, member: discord.Member = None):
        a = ctx.author.display_name; b = member.display_name if member else "todos"
        count = get_contador(ctx.author.id, member.id if member else 0, accion)
        msg   = info["msg"].format(a=a, b=b)
        gif   = await obtener_gif_anime(info["gif_tag"])
        embed = discord.Embed(description=f"**{msg}**", color=discord.Color.red())
        if gif: embed.set_image(url=gif)
        if member and member != ctx.author:
            view = AnimeView(ctx.author, member, accion, info)
            await ctx.send(embed=embed, view=view)
        else: await ctx.send(embed=embed)
    _cmd.__name__ = accion

for _a, _i in ANIME_ACCIONES.items():
    make_anime_cmd(_a, _i)


# ═════════════════════════════════════════════════════════════
#  📖 AYUDA
# ═════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
#  🔴 INTERFAZ ESTILO ZYROX — Paginación + Dropdown + Userinfo
#  Reemplaza: ayuda, _build_ayuda_embed, userinfo
# ═══════════════════════════════════════════════════════════════

# ── Páginas del menú de ayuda ─────────────────────────────────
def _get_help_pages(p: str):
    """Devuelve lista de embeds para el menú paginado."""
    RED = 0xFF0000

    pages = []

    # ─── Página 1: Inicio ─────────────────────────────────────
    e = discord.Embed(
        title="🤖 Bienvenido al Panel de Ayuda",
        description=(
            f"**Prefijo del servidor:** `{p}`\n"
            f"**Total de comandos:** `100+`\n\n"
            f"Usa los botones ⬅️ ➡️ para navegar,\n"
            f"o el menú desplegable para ir directo a una sección.\n\n"
            f"*Escribe `{p}ayuda` para ver este menú.*"
        ),
        color=RED
    )
    e.add_field(name="🔴 Comandos Principales",
        value="Moderación · AntiNuke · Roles · Canales · Warns", inline=True)
    e.add_field(name="🎮 Comandos Extra",
        value="Juegos · Fun · Anime · Roleplay · Cumpleaños", inline=True)
    pages.append(e)

    # ─── Página 2: Generales ─────────────────────────────────
    e = discord.Embed(title="🌐 Comandos Generales", color=RED)
    e.add_field(name="Información",
        value=(
            f"`{p}ping` · `{p}avatar` · `{p}banner`\n"
            f"`{p}userinfo` · `{p}serverinfo`\n"
            f"`{p}stats` · `{p}botinfo` · `{p}invitar`"
        ), inline=False)
    e.add_field(name="Utilidades",
        value=(
            f"`{p}clima <ciudad>` — Clima actual\n"
            f"`{p}tr <idioma> <texto>` — Traducir\n"
            f"`{p}calc <expr>` — Calculadora\n"
            f"`{p}color <hex>` — Ver color\n"
            f"`{p}buscar <texto>` — Google\n"
            f"`{p}rng [min] [max]` — Número aleatorio\n"
            f"`{p}recordar <tiempo> <msg>` — Recordatorio\n"
            f"`{p}sugerencia <txt>` — Enviar sugerencia\n"
            f"`{p}reporte @user <razón>` — Reportar"
        ), inline=False)
    pages.append(e)

    # ─── Página 3: AntiNuke ───────────────────────────────────
    e = discord.Embed(title="🛡️ Comandos AntiNuke", color=RED)
    e.add_field(name="General",
        value=(
            f"`{p}antinuke` — Panel completo\n"
            f"`{p}an_ayuda` — Lista de comandos\n"
            f"`{p}an_activar` / `{p}an_desactivar`\n"
            f"`{p}an_accion <ban/kick/strip>` — Acción al nuke\n"
            f"`{p}an_limite <tipo> <n>` — Límite de acciones\n"
            f"`{p}an_ventana <seg>` — Ventana de tiempo\n"
            f"`{p}an_owner @user` — Asignar owner\n"
            f"`{p}an_logs #canal` — Canal de logs"
        ), inline=False)
    e.add_field(name="Whitelist",
        value=(
            f"`{p}an_whitelist @user` — Añadir\n"
            f"`{p}an_whitelist remove @user` — Quitar\n"
            f"`{p}an_whitelist list` — Ver lista"
        ), inline=False)
    e.add_field(name="Módulos",
        value=(
            f"`{p}an_antiraid_on/off` — AntiRaid\n"
            f"`{p}an_antilinks_on/off` — AntiLinks\n"
            f"`{p}an_antispam_on/off` — AntiSpam\n"
            f"`{p}an_antibot_on/off` — AntiBot"
        ), inline=False)
    pages.append(e)

    # ─── Página 4: Moderación ────────────────────────────────
    e = discord.Embed(title="🔒 Comandos de Moderación", color=RED,
        description="*Requieren permiso de Administrador*")
    e.add_field(name="Sanciones",
        value=(
            f"`{p}ban @u [razón]` — Banear\n"
            f"`{p}unban <user>` — Desbanear\n"
            f"`{p}kick @u [razón]` — Expulsar\n"
            f"`{p}mute @u [minutos]` — Silenciar\n"
            f"`{p}unmute @u` — Des-silenciar"
        ), inline=True)
    e.add_field(name="Mensajes",
        value=(
            f"`{p}limpiar [n]` — Purgar mensajes\n"
            f"`{p}limpiar_bots` — Purgar bots\n"
            f"`{p}limpiar_usuario @u` — Purgar de user"
        ), inline=True)
    e.add_field(name="Nicks",
        value=(
            f"`{p}nick @u <nuevo>` — Cambiar nick\n"
            f"`{p}massnick <nick>` — Nick masivo"
        ), inline=False)
    pages.append(e)

    # ─── Página 5: Warns ─────────────────────────────────────
    e = discord.Embed(title="⚠️ Sistema de Warns", color=RED,
        description="*Requieren rol de Staff o Administrador*")
    e.add_field(name="Comandos",
        value=(
            f"`{p}warn @u <razón>` — Advertir\n"
            f"`{p}warns [@u]` — Ver advertencias\n"
            f"`{p}clearwarns @u` — Borrar todas\n"
            f"`{p}delwarn @u <n>` — Borrar warn #n"
        ), inline=False)
    pages.append(e)

    # ─── Página 6: Canales ───────────────────────────────────
    e = discord.Embed(title="💬 Comandos de Canales", color=RED,
        description="*Requieren permiso de Administrador*")
    e.add_field(name="Control",
        value=(
            f"`{p}lock` / `{p}unlock` — Bloquear canal\n"
            f"`{p}lockall` / `{p}unlockall` — Bloquear todos\n"
            f"`{p}hide` / `{p}show` — Ocultar canal\n"
            f"`{p}slowmode [seg]` — Modo lento\n"
            f"`{p}topic <txt>` — Cambiar tema"
        ), inline=True)
    e.add_field(name="Gestión",
        value=(
            f"`{p}cc <nombre>` — Crear canal\n"
            f"`{p}ec` — Eliminar canal\n"
            f"`{p}rc <nombre>` — Renombrar canal\n"
            f"`{p}clone` — Clonar canal\n"
            f"`{p}nsfw` — Toggle NSFW"
        ), inline=True)
    pages.append(e)

    # ─── Página 7: Roles ─────────────────────────────────────
    e = discord.Embed(title="🎭 Comandos de Roles", color=RED,
        description="*Requieren permiso de Administrador*")
    e.add_field(name="Usuarios",
        value=(
            f"`{p}dr @u <rol>` — Dar rol\n"
            f"`{p}qr @u <rol>` — Quitar rol\n"
            f"`{p}ru [@u]` — Listar roles del user\n"
            f"`{p}v @u` — Dar acceso ARN"
        ), inline=True)
    e.add_field(name="Gestión",
        value=(
            f"`{p}cr #color <nombre>` — Crear rol\n"
            f"`{p}er <nombre>` — Eliminar rol\n"
            f"`{p}lroles` — Listar roles"
        ), inline=True)
    e.add_field(name="Anuncios",
        value=(
            f"`{p}ann [#c] <msg>` — Anuncio\n"
            f"`{p}emb [#c] \"titulo\" <msg>` — Embed"
        ), inline=False)
    pages.append(e)

    # ─── Página 8: Juegos ────────────────────────────────────
    e = discord.Embed(title="🎰 Comandos de Juegos", color=RED)
    e.add_field(name="Entretenimiento",
        value=(
            f"`{p}trivia` — Pregunta trivia\n"
            f"`{p}adivina [max]` — Adivina el número\n"
            f"`{p}acertijo` — Acertijo aleatorio\n"
            f"`{p}tor [@u]` — Verdad o Reto\n"
            f"`{p}8ball <preg>` — Bola 8 mágica\n"
            f"`{p}piedra` — Piedra Papel Tijera"
        ), inline=True)
    e.add_field(name="Azar",
        value=(
            f"`{p}dado [lados]` — Tirar dado\n"
            f"`{p}dp [n] [lados]` — Dados personalizados\n"
            f"`{p}moneda` — Cara o cruz\n"
            f"`{p}ruleta op1 op2...` — Ruleta"
        ), inline=True)
    pages.append(e)

    # ─── Página 9: Sorteos y Encuestas ───────────────────────
    e = discord.Embed(title="🎁 Sorteos y Encuestas", color=RED,
        description="*Requieren rol de Staff*")
    e.add_field(name="Sorteos",
        value=f"`{p}sorteo <segundos> <premio>` — Iniciar sorteo", inline=False)
    e.add_field(name="Encuestas",
        value=(
            f"`{p}encuesta <preg> | op1 | op2` — Encuesta\n"
            f"`{p}encuesta_si_no <pregunta>` — Sí / No"
        ), inline=False)
    pages.append(e)

    # ─── Página 10: Roleplay ─────────────────────────────────
    e = discord.Embed(title="🎭 Roleplay", color=RED)
    e.add_field(name="Parejas",
        value=(
            f"`{p}casar @u` — Proponer matrimonio\n"
            f"`{p}aceptar` — Aceptar propuesta\n"
            f"`{p}rechazar` — Rechazar propuesta\n"
            f"`{p}divorcio` — Divorciarse\n"
            f"`{p}pareja` — Ver tu pareja"
        ), inline=True)
    e.add_field(name="Familia",
        value=(
            f"`{p}adoptar @u` — Adoptar\n"
            f"`{p}familia` — Ver tu familia"
        ), inline=True)
    pages.append(e)

    # ─── Página 11: Fun ──────────────────────────────────────
    e = discord.Embed(title="🔮 Comandos Fun", color=RED)
    e.add_field(name="Personalidad",
        value=(
            f"`{p}horoscopo <signo>` — Horóscopo\n"
            f"`{p}personalidad` — Test de personalidad\n"
            f"`{p}compatibilidad @u` — Compatibilidad"
        ), inline=True)
    e.add_field(name="Entretenimiento",
        value=(
            f"`{p}frase` — Frase motivacional\n"
            f"`{p}chiste` — Chiste aleatorio\n"
            f"`{p}meme` — Meme random\n"
            f"`{p}fp [personaje]` — Frase de personaje\n"
            f"`{p}pl` — Frases de anime"
        ), inline=True)
    pages.append(e)

    # ─── Página 12: Anime ────────────────────────────────────
    e = discord.Embed(title="🐱 Comandos Anime", color=RED,
        description="Interactúa con otros usuarios con GIFs de anime")
    e.add_field(name="Comandos",
        value=(
            f"`{p}abrazar @u` · `{p}pat @u` · `{p}slap @u`\n"
            f"`{p}kiss @u` · `{p}poke @u` · `{p}cuddle @u`\n"
            f"`{p}bite @u` · `{p}wave @u` · `{p}dance`\n"
            f"`{p}cry`"
        ), inline=False)
    pages.append(e)

    # ─── Página 13: Cumpleaños y Recordatorios ───────────────
    e = discord.Embed(title="🎂 Cumpleaños y ⏰ Recordatorios", color=RED)
    e.add_field(name="Cumpleaños",
        value=(
            f"`{p}cumple [DD/MM]` — Registrar cumpleaños\n"
            f"`{p}cumple_ver [@u]` — Ver cumpleaños\n"
            f"`{p}cumples_lista` — Lista del servidor"
        ), inline=False)
    e.add_field(name="Recordatorios",
        value=f"`{p}recordar <10m/2h/30s> <msg>` — Crear recordatorio",
        inline=False)
    pages.append(e)

    # ─── Página 14: Config ───────────────────────────────────
    e = discord.Embed(title="⚙️ Configuración", color=RED)
    e.add_field(name="Bot",
        value=f"`{p}setprefix <nuevo>` — Cambiar prefijo del servidor",
        inline=False)
    pages.append(e)

    # Añadir numeración de página a todos los embeds
    total = len(pages)
    for i, page in enumerate(pages):
        page.set_footer(text=f"📖 Página {i+1}/{total} • Usa los botones para navegar")

    return pages


# ── Vista de paginación con botones y dropdown ────────────────
class AyudaView(discord.ui.View):
    """Vista interactiva de ayuda paginada al estilo ZyroX."""

    CATEGORIES = {
        "main": [
            ("🌐 Generales",        1),
            ("🛡️ AntiNuke",         2),
            ("🔒 Moderación",       3),
            ("⚠️ Warns",            4),
            ("💬 Canales",          5),
            ("🎭 Roles",            6),
        ],
        "extra": [
            ("🎰 Juegos",           7),
            ("🎁 Sorteos",          8),
            ("🎭 Roleplay",         9),
            ("🔮 Fun",             10),
            ("🐱 Anime",           11),
            ("🎂 Cumpleaños",      12),
            ("⚙️ Config",          13),
        ],
    }

    def __init__(self, pages: list, author_id: int):
        super().__init__(timeout=120)
        self.pages    = pages
        self.current  = 0
        self.author   = author_id
        self._build_select()

    # ── Dropdown ──────────────────────────────────────────────
    def _build_select(self):
        # Dropdown Comandos Principales
        main_select = discord.ui.Select(
            placeholder="📋 Comandos Principales",
            min_values=1, max_values=1, row=1,
            options=[
                discord.SelectOption(label=name, value=str(idx), emoji="🔴")
                for name, idx in self.CATEGORIES["main"]
            ]
        )
        main_select.callback = self._select_callback
        self.add_item(main_select)

        # Dropdown Comandos Extra
        extra_select = discord.ui.Select(
            placeholder="🎮 Comandos Extra",
            min_values=1, max_values=1, row=2,
            options=[
                discord.SelectOption(label=name, value=str(idx), emoji="🎯")
                for name, idx in self.CATEGORIES["extra"]
            ]
        )
        extra_select.callback = self._select_callback
        self.add_item(extra_select)

    async def _select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author:
            return await interaction.response.send_message(
                "❌ Solo el que invocó el comando puede usar esto.", ephemeral=True)
        self.current = int(interaction.data["values"][0])
        await interaction.response.edit_message(
            embed=self.pages[self.current], view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # dejamos pasar; cada botón valida por dentro

    # ── Botones ───────────────────────────────────────────────
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.grey, row=0)
    async def first(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.author:
            return await interaction.response.send_message("❌ No es tu menú.", ephemeral=True)
        self.current = 0
        await interaction.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple, row=0)
    async def prev(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.author:
            return await interaction.response.send_message("❌ No es tu menú.", ephemeral=True)
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.danger, row=0)
    async def delete(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.author:
            return await interaction.response.send_message("❌ No es tu menú.", ephemeral=True)
        await interaction.message.delete()

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple, row=0)
    async def next(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.author:
            return await interaction.response.send_message("❌ No es tu menú.", ephemeral=True)
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.grey, row=0)
    async def last(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.author:
            return await interaction.response.send_message("❌ No es tu menú.", ephemeral=True)
        self.current = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── Comando !ayuda con interfaz paginada ─────────────────────
@bot.command(name="ayuda", aliases=["help","h","comandos"])
async def ayuda(ctx):
    pages = _get_help_pages(PREFIX)
    view  = AyudaView(pages, ctx.author.id)
    await ctx.send(embed=pages[0], view=view)

@bot.tree.command(name="ayuda", description="📖 Muestra todos los comandos del bot")
async def ayuda_slash(interaction: discord.Interaction):
    pages = _get_help_pages(PREFIX)
    view  = AyudaView(pages, interaction.user.id)
    await interaction.response.send_message(embed=pages[0], view=view)


# ── Comando !userinfo estilo ZyroX ────────────────────────────
@bot.command(name="userinfo", aliases=["ui","whois","info"])
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    # ── Roles (sin @everyone) ─────────────────────────────────
    roles = [r for r in reversed(member.roles) if r != ctx.guild.default_role]
    highest_role = roles[0] if roles else None
    roles_mention = " ".join(r.mention for r in roles[:10]) or "Sin roles"
    if len(roles) > 10:
        roles_mention += f" *+{len(roles)-10} más*"

    # ── Insignias ─────────────────────────────────────────────
    badges = []
    flags = member.public_flags
    if flags.hypesquad_bravery:    badges.append("HypeSquad Bravery")
    if flags.hypesquad_brilliance: badges.append("HypeSquad Brilliance")
    if flags.hypesquad_balance:    badges.append("HypeSquad Balance")
    if flags.early_supporter:      badges.append("Early Supporter")
    if flags.bug_hunter:           badges.append("Bug Hunter")
    if flags.bug_hunter_level_2:   badges.append("Bug Hunter Gold")
    if flags.verified_bot_developer: badges.append("Bot Developer")
    if flags.partner:              badges.append("Discord Partner")
    if flags.staff:                badges.append("Discord Staff")
    badges_str = " · ".join(badges) if badges else "Ninguna"

    # ── Permisos clave ────────────────────────────────────────
    PERMS_CLAVE = {
        "administrator":       "Administrator",
        "ban_members":         "Ban Members",
        "kick_members":        "Kick Members",
        "manage_guild":        "Manage Server",
        "manage_messages":     "Manage Messages",
        "manage_roles":        "Manage Roles",
        "manage_channels":     "Manage Channels",
        "manage_nicknames":    "Manage Nicknames",
        "manage_webhooks":     "Manage Webhooks",
        "manage_emojis":       "Manage Emojis",
        "mention_everyone":    "Mention Everyone",
        "moderate_members":    "Moderate Members",
    }
    perms = member.guild_permissions
    active_perms = [label for attr, label in PERMS_CLAVE.items() if getattr(perms, attr, False)]
    perms_str = " , ".join(active_perms) if active_perms else "Ninguno"

    # ── Reconocimiento ────────────────────────────────────────
    if member.id == ctx.guild.owner_id:
        ack = "Server Owner"
    elif perms.administrator:
        ack = "Server Admin"
    elif perms.manage_guild:
        ack = "Server Manager"
    elif perms.manage_messages:
        ack = "Server Moderator"
    else:
        ack = "Server Member"

    # ── Voz y Boost ───────────────────────────────────────────
    voz      = member.voice.channel.mention if member.voice else "None"
    boosting = f"Since {member.premium_since.strftime('%d/%m/%Y')}" if member.premium_since else "None"

    # ── Fechas ────────────────────────────────────────────────
    acc_created  = member.created_at.strftime("%d/%m/%Y")
    guild_joined = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "?"

    # ── Construir embed ───────────────────────────────────────
    embed = discord.Embed(
        title=f"{member}'s Information",
        color=highest_role.color if highest_role and highest_role.color.value else 0xFF0000
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="__General Information__",
        value=(
            f"**Name:** {member.name}\n"
            f"**ID:** {member.id}\n"
            f"**Nickname:** {member.nick or 'None'}\n"
            f"**Bot?:** {'✅ Yes' if member.bot else '❌ No'}\n"
            f"**Badges:** {badges_str}\n"
            f"**Account Created:** {acc_created}\n"
            f"**Server Joined:** {guild_joined}"
        ), inline=False)

    embed.add_field(name="__Role Info__",
        value=(
            f"**Highest Role:** {highest_role.mention if highest_role else 'None'}\n"
            f"**Roles ({len(roles)}):** {roles_mention}\n"
            f"**Color:** `{str(member.color)}`"
        ), inline=False)

    embed.add_field(name="__Extra__",
        value=(
            f"**Boosting:** {boosting}\n"
            f"**Voice:** {voz}"
        ), inline=False)

    embed.add_field(name="__Key Permissions__",
        value=perms_str, inline=False)

    embed.add_field(name="__Acknowledgement__",
        value=ack, inline=False)

    now = datetime.now(timezone.utc).strftime("%I:%M %p")
    embed.set_footer(
        text=f"Requested by {ctx.author} • Today at {now}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)



# ─────────────────────────────────────────────────────────────
#  EVENTOS
# ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    # ── Sincronizar slash commands ──────────────────────────
    try:
        synced = await bot.tree.sync()
        log.info(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        log.error(f"Error al sincronizar slash commands: {e}")

    # ── Presencia ───────────────────────────────────────────
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"!ayuda | /ayuda | AntiNuke"
        )
    )

    # ── Banner rojo en consola ──────────────────────────────
    mostrar_banner(bot_user=bot.user, guild_count=len(bot.guilds))
    log.info(f"Bot listo: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 No tienes permisos para ese comando.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Miembro no encontrado.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Argumento inválido. Usa `{PREFIX}ayuda`.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Falta un argumento. Usa `{PREFIX}ayuda`.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        log.error(f"Error en '{ctx.command}': {error}\n{traceback.format_exc()}")
        await ctx.send(f"⚠️ Error: `{error}`")


# ─────────────────────────────────────────────────────────────
#  INICIO
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{R}{'═'*64}{RS}")
    print(f"  {BW}Exagon Bot — Iniciando...{RS}")
    print(f"  {GR}Prefix activo:{RS} {BR}!{RS}  {GR}+{RS}  {BR}/{RS}")
    print(f"{R}{'═'*64}{RS}\n")

    while True:
        try:
            log.info("Iniciando bot...")
            bot.run(TOKEN, reconnect=True)
        except discord.LoginFailure:
            log.critical("TOKEN INVÁLIDO")
            sys.exit(1)
        except KeyboardInterrupt:
            log.info("Detenido.")
            sys.exit(0)
        except Exception:
            log.error(f"Error:\n{traceback.format_exc()}")
            log.info("Reiniciando en 5s...")
            time.sleep(5)
