from __future__ import annotations

from luminesk_cli.cores.allay import AllayCore
from luminesk_cli.cores.better_altay import BetterAltayCore
from luminesk_cli.cores.dragonfly import DragonflyCore
from luminesk_cli.cores.endstone import EndstoneCore
from luminesk_cli.cores.lumi import LumiCore
from luminesk_cli.cores.lunacy import LunacyCore
from luminesk_cli.cores.nukkit import NukkitCore
from luminesk_cli.cores.nukkit_mot import NukkitMotCore
from luminesk_cli.cores.pnx import PowerNukkitXCore
from luminesk_cli.cores.pocketmine import PocketMineCore
from luminesk_cli.cores.pumpkin import PumpkinCore
from luminesk_cli.cores.serenity import SerenityCore

ALL_CORES = [
    NukkitCore,
    PowerNukkitXCore,
    NukkitMotCore,
    LumiCore,
    AllayCore,
    PocketMineCore,
    BetterAltayCore,
    LunacyCore,
    DragonflyCore,
    PumpkinCore,
    SerenityCore,
    EndstoneCore,
]
