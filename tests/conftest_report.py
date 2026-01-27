"""
Plugin pytest pour un affichage clair et lisible des tests.

Affiche:
- Des bannieres de section par module et par classe
- Le detail de chaque test avec son resultat
- Un recapitulatif final avec compteurs
"""

import os
import time
import logging
import sys
import threading
import pytest


# -- Couleurs ANSI --------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[37m"
MAGENTA = "\033[35m"

BG_GREEN = "\033[42m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_CYAN = "\033[46m"

# -- Labels des modules ----------------------------------------------------
MODULE_LABELS = {
    "test_attacks": "ATTAQUES",
    "test_defenses": "DEFENSES",
    "test_llm_simulator": "SIMULATEUR LLM",
    "test_streaming": "STREAMING / TEST RUNNER",
    "test_web_api": "API WEB",
    "test_bombard": "BOMBARDEMENT / STRESS",
}


def _module_key(nodeid: str) -> str:
    """Extrait le nom du module depuis le nodeid."""
    filename = nodeid.split("::")[0].split("/")[-1]
    return filename.replace(".py", "")


def _class_name(nodeid: str) -> str:
    """Extrait le nom de la classe depuis le nodeid."""
    parts = nodeid.split("::")
    if len(parts) >= 2:
        return parts[1]
    return ""


# -- Spinner ---------------------------------------------------------------

def _raw_write(text):
    """Ecrit directement sur le stdout original, jamais capture."""
    try:
        sys.__stdout__.write(text)
        sys.__stdout__.flush()
    except Exception:
        pass


class Spinner:
    """Spinner anime qui montre qu'un test est en cours d'execution."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        self._running = False
        self._thread = None
        self._label = ""

    def start(self, label):
        """Demarre le spinner avec un label."""
        self._label = label
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        """Arrete le spinner et efface la ligne."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
        _raw_write(f"\r\033[K")

    def _spin(self):
        idx = 0
        while self._running:
            frame = self.FRAMES[idx % len(self.FRAMES)]
            _raw_write(f"\r    {YELLOW}{frame} {self._label}...{RESET}\033[K")
            idx += 1
            time.sleep(0.1)


# -- Plugin ----------------------------------------------------------------

class ClearReportPlugin:
    """Plugin qui affiche un rapport clair avec bannieres et progression."""

    def __init__(self):
        self.current_module = None
        self.current_class = None
        self.results = []
        self.start_time = None
        self.module_stats = {}
        self._test_index = 0
        self._total_tests = 0
        self._spinner = Spinner()

    def _out(self, text=""):
        """Ecrit sur le stdout original (sys.__stdout__), jamais capture."""
        _raw_write(text + "\n")

    # -- Hooks pytest -------------------------------------------------------

    @pytest.hookimpl(trylast=True)
    def pytest_sessionstart(self, session):
        """Redirige le terminal reporter vers /dev/null pour supprimer les points."""
        tr = session.config.pluginmanager.getplugin("terminalreporter")
        if tr and hasattr(tr, "_tw"):
            tr._tw._file = open(os.devnull, "w")

    def pytest_collection_modifyitems(self, config, items):
        """Trie les tests par module puis par classe pour un affichage groupe."""
        items.sort(key=lambda item: (
            item.fspath.basename,
            item.cls.__name__ if item.cls else "",
            item.name,
        ))

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtestloop(self, session):
        """Prend en charge la boucle de tests pour un affichage propre."""
        if session.testsfailed and not session.config.option.continue_on_collection_errors:
            raise session.Interrupted(
                "%d error%s during collection"
                % (session.testsfailed, "s" if session.testsfailed != 1 else "")
            )

        if session.config.option.collectonly:
            return True

        # Reduire le bruit des loggers internes
        for name in ["attack_engine", "llm_attack_lab", "llm_simulator", "werkzeug"]:
            logging.getLogger(name).setLevel(logging.ERROR)

        self.start_time = time.time()
        self._total_tests = len(session.items)

        self._out()
        self._out(f"{BOLD}{BG_CYAN}{WHITE} LLM ATTACK LAB - TESTS {RESET}")
        self._out(f"{CYAN}{'=' * 60}{RESET}")
        self._out(f"{DIM}  {self._total_tests} tests a executer{RESET}")
        self._out(f"{CYAN}{'=' * 60}{RESET}")

        try:
            for i, item in enumerate(session.items):
                self._test_index = i + 1

                nextitem = session.items[i + 1] if i + 1 < len(session.items) else None

                # Afficher les bannieres avant le test
                self._print_headers(item)

                # Afficher le spinner pendant l'execution du test
                test_name = item.nodeid.split("::")[-1]
                progress = f"[{self._test_index}/{self._total_tests}]"
                self._spinner.start(f"{progress} {test_name}")

                item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)

                if session.shouldfail:
                    raise session.Failed(session.shouldfail)
                if session.shouldstop:
                    raise session.Interrupted(session.shouldstop)
        except (session.Failed, session.Interrupted):
            self._spinner.stop()
            raise
        except Exception as exc:
            self._spinner.stop()
            self._out(f"\n    {RED}[ERREUR BOUCLE] Test {self._test_index}: {exc}{RESET}")
        finally:
            self._spinner.stop()
            self._print_summary()

        return True

    def _print_headers(self, item):
        """Affiche les bannieres de module/classe si necessaire."""
        mod = _module_key(item.nodeid)
        cls = _class_name(item.nodeid)

        if mod != self.current_module:
            self.current_module = mod
            self.current_class = None
            label = MODULE_LABELS.get(mod, mod.upper())
            self._out()
            self._out(f"{BOLD}{MAGENTA}{'#' * 60}{RESET}")
            self._out(f"{BOLD}{MAGENTA}#  {label}{RESET}")
            self._out(f"{BOLD}{MAGENTA}{'#' * 60}{RESET}")
            self.module_stats[mod] = {"passed": 0, "failed": 0, "skipped": 0}

        if cls and cls != self.current_class:
            self.current_class = cls
            class_doc = ""
            if item.cls and item.cls.__doc__:
                first_line = item.cls.__doc__.strip().split("\n")[0]
                class_doc = f" -- {first_line}"
            self._out()
            self._out(f"  {BOLD}{CYAN}[{cls}]{RESET}{DIM}{class_doc}{RESET}")
            self._out(f"  {CYAN}{'-' * 56}{RESET}")

    def pytest_runtest_logreport(self, report):
        """Affiche le resultat de chaque test."""
        try:
            if report.when != "call" and not (report.when == "setup" and report.failed):
                return

            # Arreter le spinner avant d'afficher le resultat
            self._spinner.stop()

            nodeid = report.nodeid
            mod = _module_key(nodeid)

            # Nom court du test
            test_name = nodeid.split("::")[-1]

            if report.passed:
                icon = f"{GREEN}PASS{RESET}"
                self.results.append(("passed", nodeid))
                if mod in self.module_stats:
                    self.module_stats[mod]["passed"] += 1
            elif report.failed:
                icon = f"{RED}FAIL{RESET}"
                self.results.append(("failed", nodeid))
                if mod in self.module_stats:
                    self.module_stats[mod]["failed"] += 1
            elif report.skipped:
                icon = f"{YELLOW}SKIP{RESET}"
                self.results.append(("skipped", nodeid))
                if mod in self.module_stats:
                    self.module_stats[mod]["skipped"] += 1
            else:
                return

            duration = f"{report.duration:.3f}s" if report.duration else ""
            progress = f"[{self._test_index}/{self._total_tests}]"
            self._out(f"    {icon}  {test_name}  {DIM}{duration}  {progress}{RESET}")

            # Si echec, afficher le detail
            if report.failed and report.longreprtext:
                self._out()
                for line in report.longreprtext.split("\n"):
                    self._out(f"         {RED}{line}{RESET}")
                self._out()
        except Exception as exc:
            self._out(f"    {RED}[ERREUR PLUGIN] {exc}{RESET}")

    def _print_summary(self):
        """Affiche le recapitulatif final."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        passed = sum(1 for s, _ in self.results if s == "passed")
        failed = sum(1 for s, _ in self.results if s == "failed")
        skipped = sum(1 for s, _ in self.results if s == "skipped")
        total = len(self.results)

        self._out()
        self._out(f"{BOLD}{'=' * 60}{RESET}")
        self._out(f"{BOLD}  RECAPITULATIF{RESET}")
        self._out(f"{'=' * 60}")
        self._out()

        # Stats par module
        for mod, stats in self.module_stats.items():
            label = MODULE_LABELS.get(mod, mod)
            p = stats["passed"]
            f = stats["failed"]
            s = stats["skipped"]
            mod_total = p + f + s
            status_color = GREEN if f == 0 else RED
            self._out(f"  {status_color}{label:.<40} {p}/{mod_total} OK{RESET}")

        self._out()
        self._out(f"  {BOLD}Total: {total} tests{RESET}")
        self._out(f"    {GREEN}Passes:  {passed}{RESET}")
        if failed:
            self._out(f"    {RED}Echoues: {failed}{RESET}")
        if skipped:
            self._out(f"    {YELLOW}Ignores: {skipped}{RESET}")
        self._out(f"    {DIM}Duree:   {elapsed:.2f}s{RESET}")
        self._out()

        if failed == 0:
            self._out(f"  {BG_GREEN}{WHITE}{BOLD} TOUS LES TESTS PASSENT {RESET}")
        else:
            self._out(f"  {BG_RED}{WHITE}{BOLD} {failed} TEST(S) EN ECHEC {RESET}")
            self._out()
            self._out(f"  Tests echoues:")
            for status, nodeid in self.results:
                if status == "failed":
                    self._out(f"    {RED}- {nodeid}{RESET}")

        self._out()


def pytest_configure(config):
    """Enregistre le plugin de rapport clair."""
    if not hasattr(config, "_clear_report_registered"):
        config._clear_report_registered = True
        config.pluginmanager.register(ClearReportPlugin(), "clear_report")

        # Reduire le bruit des loggers applicatifs des la configuration
        for name in ["attack_engine", "llm_attack_lab", "llm_simulator",
                      "werkzeug", "llm_attack_lab.monitoring"]:
            logging.getLogger(name).setLevel(logging.CRITICAL)

        # Silence le LabLogger custom du projet
        try:
            from llm_attack_lab.monitoring.logger import get_logger, LogLevel
            lab_logger = get_logger()
            lab_logger.level = LogLevel.CRITICAL
        except ImportError:
            pass
