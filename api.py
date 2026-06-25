import discord
from discord.ext import commands
import aiohttp
import json
import os
from datetime import datetime
from typing import Optional

TOKEN = "MTUxODA4NDk0MTA1MTg1NDg5OQ.GO4L_f.0ilXR7qaXDRACVeabKEQIywHWk7MPOswXOTqM8"
PANEL_CHANNEL_ID = 1503503368176402606

GTC_API_URL = "https://gtccheats.xyz/Api/uidbypassapi/api_user.php"
GTC_API_KEY = "GTCAPI-A47E3C697AD1BCCB81FC8D7E64972A90"
DIAS_AVISO_BAJOS = 3

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def gtc_add_uid(uid: str, days: int, note: str = "") -> dict:
    headers = {"X-API-KEY": GTC_API_KEY, "Authorization": f"Bearer {GTC_API_KEY}", "Content-Type": "application/json"}
    params = {"action": "add"}
    payload = {"account_id": uid, "for_days": days, "api_key": GTC_API_KEY, "note": note}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GTC_API_URL, headers=headers, params=params, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else None
                except Exception:
                    data = None
                return {"success": resp.status < 300, "status": resp.status, "data": data, "text": text}
    except Exception as e:
        return {"success": False, "status": 0, "data": {"error": str(e)}, "text": ""}


def _load_registry(path: str = "uids_registry.json") -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_registry(registry: dict, path: str = "uids_registry.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


async def gtc_remove_uid(uid: str) -> dict:
    headers = {"X-API-KEY": GTC_API_KEY, "Authorization": f"Bearer {GTC_API_KEY}", "Content-Type": "application/json"}
    params = {"action": "remove"}
    payload = {"account_id": uid, "api_key": GTC_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GTC_API_URL, headers=headers, params=params, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else None
                except Exception:
                    data = None
                return {"success": resp.status < 300, "status": resp.status, "data": data, "text": text}
    except Exception as e:
        return {"success": False, "status": 0, "data": {"error": str(e)}, "text": ""}


def _remove_uid_from_registry(uid: str, path: str = "uids_registry.json") -> bool:
    registry = _load_registry(path)
    if uid in registry:
        del registry[uid]
        _save_registry(registry, path)
        return True
    return False


@bot.event
async def on_ready():
    print(f"Bot EXE listo como {bot.user.name}")
    print(f"Escuchando canal: {PANEL_CHANNEL_ID}")
    print(f"API: {GTC_API_URL}")


@bot.event
async def on_message(message):
    # Bloquear otros bots, permitir mensajes del propio bot (el EXE usa este token)
    if message.author.bot and message.author.id != bot.user.id:
        return

    if message.channel.id == PANEL_CHANNEL_ID:
        print(f"Mensaje: {message.content[:60]}")

        # Formato desde EXE: AGIEGAR:UID:DIAS:NOTA
        if message.content.startswith("AGREGAR:"):
            try:
                parts = message.content.split(":")
                if len(parts) < 3:
                    await message.delete()
                    return

                uid = parts[1].strip().upper()
                days = int(parts[2].strip())
                note = parts[3].strip() if len(parts) >= 4 else "Desde EXE"
                infinito = days >= 36500
                dias_display = "Infinito" if infinito else str(days)
                print(f"UID={uid} dias={dias_display} nota={note}")

                channel = bot.get_channel(PANEL_CHANNEL_ID)
                await message.delete()

                # Aviso si la key tiene pocos dias (solo si no es infinita)
                if not infinito and days <= DIAS_AVISO_BAJOS:
                    aviso = discord.Embed(
                        title="Key proxima a vencer",
                        description=f"UID {uid} tiene solo {days} dia(s). Renueva tu key!",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    aviso.set_footer(text="Cosmos Auth")
                    if channel:
                        await channel.send(embed=aviso)

                # Llamar API directamente
                result = await gtc_add_uid(uid, days, note)
                print(f"API result: {result}")

                ok = result["success"]
                if ok:
                    desc = f"UID {uid} autorizado — Duracion: {dias_display}."
                    titulo = "UID Agregado"
                    color = discord.Color.green()
                    # Persistir en el registro local
                    try:
                        registry = _load_registry("uids_registry.json")
                        entry = {
                            "bot": "UID Bot",
                            "days": days,
                            "added_at": datetime.now().isoformat(),
                            "note": note,
                            "expired_logged_at": None,
                        }
                        registry.setdefault(uid, []).append(entry)
                        _save_registry(registry, "uids_registry.json")
                    except Exception as e:
                        print(f"Error guardando registry: {e}")
                else:
                    # Mejor presentación de la respuesta: mostrar texto si no hay JSON
                    resp_display = result.get("data") if result.get("data") is not None else result.get("text")
                    desc = f"No se pudo agregar {uid}. Respuesta: {resp_display}"
                    titulo = "Error al agregar UID"
                    color = discord.Color.red()

                embed = discord.Embed(title=titulo, description=desc, color=color, timestamp=datetime.now())
                embed.add_field(name="UID",  value=f"{uid}",        inline=True)
                embed.add_field(name="Dias", value=dias_display,     inline=True)
                embed.add_field(name="Nota", value=note or "-",      inline=True)
                embed.set_footer(text="Cosmos Auth - Bot EXE")
                if channel:
                    await channel.send(embed=embed)
                return

            except ValueError:
                await message.channel.send("Dias invalidos en AGREGAR")
                return
            except Exception as e:
                await message.channel.send(f"Error: {e}")
                return

    await bot.process_commands(message)


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Agregar", style=discord.ButtonStyle.green, custom_id="panel_add")
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Para agregar un UID manualmente, envía un mensaje en el canal con el formato: AGREGAR:UID:DIAS:NOTA", ephemeral=True)

    @discord.ui.button(label="Eliminar", style=discord.ButtonStyle.red, custom_id="panel_remove")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Para eliminar un UID manualmente ejecuta: !eliminar <UID> — el bot intentará retirar la autorización en la API y actualizar el registro local.", ephemeral=True)

    @discord.ui.button(label="Lista", style=discord.ButtonStyle.blurple, custom_id="panel_list")
    async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        registry = _load_registry("uids_registry.json")
        total = len(registry)
        embed = discord.Embed(title="Lista Activa", description=f"UIDs activos: {total}", color=discord.Color.blue(), timestamp=datetime.now())
        # Mostrar hasta 10 UIDs
        lines = []
        for i, (k, v) in enumerate(registry.items()):
            if i >= 10:
                lines.append(f"... y {len(registry)-10} más")
                break
            first = v[0] if isinstance(v, list) and v else {}
            days = first.get("days", "?")
            note = first.get("note", "-")
            lines.append(f"{k} — {days} días — {note}")
        embed.add_field(name="Entradas", value="\n".join(lines) if lines else "(vacío)", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="panel")
async def panel(ctx):
    """Muestra el panel de control con botones (Agregar / Eliminar / Lista)."""
    embed = discord.Embed(title="COSMOS UID | Panel UID", description="Centro de Autorización UID\nGestiona accesos de forma rápida y ordenada.", color=discord.Color.dark_grey())
    embed.add_field(name="Agregar UID", value="Autoriza un UID con días definidos y nota opcional.", inline=False)
    embed.add_field(name="Eliminar UID", value="Retira el acceso de un UID y actualiza la lista local.", inline=False)
    embed.add_field(name="Lista Activa", value="Consulta los UIDs vigentes registrados para este bot.", inline=False)
    view = PanelView()
    await ctx.send(embed=embed, view=view)


@bot.command(name="lista")
async def lista(ctx):
    registry = _load_registry("uids_registry.json")
    total = len(registry)
    embed = discord.Embed(title="Lista Activa", description=f"UIDs activos: {total}", color=discord.Color.blue(), timestamp=datetime.now())
    if not registry:
        embed.add_field(name="Entradas", value="(vacío)", inline=False)
    else:
        for k, v in list(registry.items())[:20]:
            first = v[0] if isinstance(v, list) and v else {}
            days = first.get("days", "?")
            note = first.get("note", "-")
            embed.add_field(name=k, value=f"{days} días — {note}", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="eliminar")
async def eliminar(ctx, uid: Optional[str] = None):
    if not uid:
        await ctx.send("Uso: !eliminar <UID>")
        return
    uid = uid.strip()
    # Llamar API para remover
    result = await gtc_remove_uid(uid)
    if result.get("success"):
        removed_local = _remove_uid_from_registry(uid, "uids_registry.json")
        desc = f"UID {uid} eliminado de la API. {'Registro local actualizado.' if removed_local else 'No existía en registro local.'}"
        color = discord.Color.green()
        title = "UID Eliminado"
    else:
        resp_display = result.get("data") if result.get("data") is not None else result.get("text")
        desc = f"No se pudo eliminar {uid}. Respuesta: {resp_display}"
        color = discord.Color.red()
        title = "Error al eliminar UID"
    embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now())
    embed.add_field(name="UID", value=uid, inline=True)
    embed.add_field(name="Resultado API", value=str(result.get("status")), inline=True)
    await ctx.send(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)
