#!/usr/bin/env python

import asyncio
import logging
import os
import typing

import decky  # type: ignore
import fling
import updater
from settings import SettingsManager  # type: ignore

# Setup environment variables
settingsDir = decky.DECKY_PLUGIN_SETTINGS_DIR
loggingDir = decky.DECKY_PLUGIN_LOG_DIR
cheatdeckHome = os.path.join(decky.DECKY_USER_HOME, "autocheatdeck")
trainersDir = os.path.join(cheatdeckHome, "trainers")
# Backups and update scratch space live outside the plugins folder so Decky never loads them
updateStateDir = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "update")


def give_to_user(path: str):
    """The backend runs as root; hand downloaded files back to the Deck user so Proton can use them."""
    home = os.stat(decky.DECKY_USER_HOME)
    uid, gid = home.st_uid, home.st_gid
    os.chown(cheatdeckHome, uid, gid)
    os.chown(trainersDir, uid, gid)
    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for name in dirs + files:
            os.chown(os.path.join(root, name), uid, gid)


# Setup backend logger
logger = decky.logger
logger.setLevel(logging.DEBUG)
logger.info("[backend] Settings path: {}".format(settingsDir))

settings = SettingsManager(name="settings", settings_directory=settingsDir)
settings.read()


class SetSettingOptions(typing.TypedDict):
    key: str
    value: typing.Any


class GetSettingOptions(typing.TypedDict):
    key: str
    defaults: typing.Any


class DownloadTrainerOptions(typing.TypedDict):
    appid: int
    url: str
    pageUrl: str
    title: str


class Plugin:
    @classmethod
    async def _main(cls):
        logger.info("[backend] Loading AutoCheatDeck!")

    @classmethod
    async def _unload(cls):
        logger.info("[backend] Unloading AutoCheatDeck!")

    @classmethod
    async def _uninstall(cls):
        logger.info("[backend] Uninstalling AutoCheatDeck!")

    @classmethod
    async def read_settings(cls):
        logger.info("[backend] Reading settings")
        return settings.read()

    @classmethod
    async def commit_settings(cls):
        logger.info("[backend] Saving settings")
        return settings.commit()

    @classmethod
    async def get_setting(cls, data: GetSettingOptions):
        value = settings.getSetting(data["key"], data["defaults"])
        logger.info("[backend] Get {}: {}".format(data["key"], value))
        return value

    @classmethod
    async def set_setting(cls, data: SetSettingOptions):
        logger.info("[backend] Set {}: {}".format(data["key"], data["value"]))
        return settings.setSetting(data["key"], data["value"])

    @classmethod
    async def _migration(cls):
        if settings.getSetting("CustomOptionsV6", None) is not None:
            return

        logger.info("[backend] Initializing custom option presets")
        settings.setSetting("CustomOptionsV6", [
            {
                "id": "preset-lossless-scaling",
                "label": "LSFG-VK Frame Generation",
                "definition": {
                    "kind": "prefix",
                    "command": "~/lsfg",
                    "argv": [],
                },
            },
            {
                "id": "preset-framegen-patch",
                "label": "Enable OptiScaler",
                "definition": {
                    "kind": "prefix",
                    "command": "~/fgmod/fgmod",
                    "argv": [],
                },
            },
            {
                "id": "preset-framegen-unpatch",
                "label": "Disable OptiScaler",
                "definition": {
                    "kind": "prefix",
                    "command": "~/fgmod/fgmod-uninstaller.sh",
                    "argv": [],
                },
            },
        ])

    @classmethod
    async def get_env(cls, env: str):
        return getattr(decky, env)

    @classmethod
    async def search_trainers(cls, name: str):
        logger.info("[backend] Searching trainers: {}".format(name))
        return await asyncio.to_thread(fling.search, name)

    @classmethod
    async def list_trainer_versions(cls, page_url: str):
        logger.info("[backend] Listing trainer versions: {}".format(page_url))
        return await asyncio.to_thread(fling.list_versions, page_url)

    @classmethod
    async def download_trainer(cls, data: DownloadTrainerOptions):
        target_dir = os.path.join(trainersDir, str(int(data["appid"])))
        logger.info("[backend] Downloading trainer {} to {}".format(data["title"], target_dir))
        result = await asyncio.to_thread(fling.download, data["url"], data["pageUrl"], target_dir)
        give_to_user(target_dir)
        logger.info("[backend] Trainer saved: {} sha256={}".format(result["path"], result["sha256"]))
        installed = settings.getSetting("InstalledTrainers", {})
        installed[str(data["appid"])] = {"title": data["title"], "pageUrl": data["pageUrl"], **result}
        settings.setSetting("InstalledTrainers", installed)
        return result

    @classmethod
    async def get_installed_trainer(cls, appid: int):
        return settings.getSetting("InstalledTrainers", {}).get(str(appid))

    @classmethod
    async def check_plugin_update(cls):
        result = await asyncio.to_thread(updater.check, decky.DECKY_PLUGIN_VERSION)
        result["hasBackup"] = updater.has_backup(updateStateDir)
        logger.info("[backend] Update check: {}".format(result))
        return result

    @classmethod
    async def install_plugin_update(cls):
        logger.info("[backend] Installing plugin update")
        version = await asyncio.to_thread(updater.install, decky.DECKY_PLUGIN_DIR, updateStateDir)
        logger.info("[backend] Installed {}, restarting Decky".format(version))
        updater.restart_loader()
        return version

    @classmethod
    async def rollback_plugin_update(cls):
        logger.info("[backend] Restoring previous plugin version")
        await asyncio.to_thread(updater.rollback, decky.DECKY_PLUGIN_DIR, updateStateDir)
        updater.restart_loader()
