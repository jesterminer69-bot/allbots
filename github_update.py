#!/usr/bin/env python3
r"""
Profit GitHub Status Updater

Reads individual bot status.json files, normalizes them into one combined
data/status.json file, then optionally commits and pushes to GitHub.

Designed for:
  C:\Users\marcg\Documents\kraken-bot\profit-github

Current source:
  Profit Monkey V2:
  C:\Users\marcg\Documents\kraken-bot\profit-monkey-v2\status\status.json

Future placeholders:
  Profit Ape, Profit Llama, Profit Alcuna
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


APP_VERSION = "1.0.1-unicode-path-fix"


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso_utc(dt: Optional[_dt.datetime] = None) -> str:
    return (dt or utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"Missing file: {path}"
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path}: {exc}"
    except Exception as exc:
        return None, f"Could not read {path}: {exc}"


def write_json(path: Path, payload: Dict[str, Any], pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def parse_updated_at(raw: Any) -> Optional[_dt.datetime]:
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        try:
            return _dt.datetime.fromtimestamp(float(raw), tz=_dt.timezone.utc)
        except Exception:
            return None
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = _dt.datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_dt.timezone.utc)
            return dt.astimezone(_dt.timezone.utc)
        except Exception:
            return None
    return None


def file_mtime_utc(path: Path) -> Optional[_dt.datetime]:
    try:
        return _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
    except Exception:
        return None


def best_number(*values: Any, default: Optional[float] = None, decimals: int = 4) -> Optional[float]:
    for v in values:
        try:
            if v is not None:
                return round(float(v), decimals)
        except Exception:
            pass
    return default


def determine_running(raw: Dict[str, Any], source_path: Path, stale_after_seconds: int) -> Tuple[str, List[str]]:
    notes: List[str] = []
    md = raw.get("master_director") or {}
    engines = md.get("engines") or []
    lanes = md.get("lanes") or []

    explicit_running = False
    if "running" in str(raw.get("message", "")).lower():
        explicit_running = True
    if str(md.get("phase", "")).strip():
        explicit_running = True
    if any(str(e.get("status", "")).lower() == "running" for e in engines if isinstance(e, dict)):
        explicit_running = True
    if any(str(l.get("status", "")).lower() in ("active", "running") for l in lanes if isinstance(l, dict)):
        explicit_running = True

    updated_dt = parse_updated_at(raw.get("updated_at")) or file_mtime_utc(source_path)
    if updated_dt is None:
        notes.append("Could not determine status file age.")
        return ("running" if explicit_running else "unknown", notes)

    age_seconds = (utc_now() - updated_dt).total_seconds()
    if age_seconds > stale_after_seconds:
        notes.append(f"Status file is stale: {int(age_seconds)} seconds old.")
        return ("idle_or_stale", notes)

    if explicit_running:
        return ("running", notes)

    return ("idle", notes)


def normalize_monkey(raw: Dict[str, Any], source_path: Path, stale_after_seconds: int) -> Dict[str, Any]:
    md = raw.get("master_director") or {}
    status, notes = determine_running(raw, source_path, stale_after_seconds)

    champions_out = []
    for c in md.get("champions") or []:
        if not isinstance(c, dict):
            continue
        regime = c.get("regime") or "UNKNOWN"
        generation = c.get("generation")
        last_promotion = (
            c.get("last_promotion_at")
            or c.get("last_promotion_time")
            or c.get("promotion_time")
            or c.get("updated_at")
        )

        champions_out.append({
            "regime": regime,
            "regime_label": f"{regime} (g{generation})" if generation is not None else regime,
            "generation": generation,
            "promotions_total": c.get("promotions_total", 0),
            "score": best_number(c.get("score"), default=None, decimals=4),
            "apr": best_number(c.get("tested_apr"), c.get("apr_after"), c.get("apr_raw"), default=0.0, decimals=4),
            "drawdown_pct": best_number(c.get("drawdown_pct"), c.get("dd_after"), default=0.0, decimals=4),
            "trades": c.get("trades", c.get("trades_after", 0)),
            "family": c.get("family", ""),
            "process": c.get("process", ""),
            "champion_id": c.get("champion_id", ""),
            "last_promotion": last_promotion or "Not reported yet"
        })

    champions_out.sort(key=lambda x: str(x.get("regime", "")))

    current_run = (
        md.get("target_mode")
        or md.get("phase")
        or raw.get("mode")
        or "Unknown"
    )

    engines = []
    for e in md.get("engines") or []:
        if isinstance(e, dict):
            engines.append({
                "name": e.get("name", "UNKNOWN"),
                "status": e.get("status", "unknown"),
                "done": e.get("done", 0),
                "total": e.get("total", 0),
                "promotions": e.get("promotions", 0)
            })

    lanes = []
    for l in md.get("lanes") or []:
        if isinstance(l, dict):
            lanes.append({
                "lane": l.get("lane"),
                "regime": l.get("regime", ""),
                "status": l.get("status", "unknown")
            })

    return {
        "id": "profit_monkey",
        "display_name": "Kraken Profit Monkey Trainer",
        "kind": "trainer",
        "available": True,
        "status": status,
        "notes": notes,
        "source_path": str(source_path),
        "source_updated_at": raw.get("updated_at") or None,
        "app": raw.get("app") or md.get("app") or "Profit Monkey",
        "version": raw.get("version") or md.get("core_version") or "",
        "current_run": current_run,
        "current_goal": raw.get("message") or md.get("dashboard_note") or current_run,
        "phase": md.get("phase") or raw.get("phase") or "",
        "director_cycle": md.get("director_cycle"),
        "aggression_mode": md.get("aggression_mode"),
        "progressive_level": md.get("progressive_level"),
        "symbol": md.get("symbol"),
        "workers": md.get("workers"),
        "workers_verified": md.get("workers_verified"),
        "estimated_apr": best_number(
            md.get("estimated_total_apr"),
            md.get("combined_estimated_apr"),
            md.get("live_estimated_apr"),
            md.get("active_champion_avg_apr"),
            default=None,
            decimals=4
        ),
        "last_combined_test_apr": best_number(md.get("last_combined_test_apr"), default=None, decimals=4),
        "last_combined_test_source": md.get("last_combined_test_source"),
        "champion_coverage_pct": best_number(md.get("champion_coverage_pct"), default=None, decimals=2),
        "active_champion_count": md.get("active_champion_count"),
        "tradable_champion_count": md.get("tradable_champion_count"),
        "dormant_champion_count": md.get("dormant_champion_count"),
        "total_promotions": md.get("total_promotions", 0),
        "phase_promotions": md.get("phase_promotions", 0),
        "children_per_parent": md.get("children_per_parent"),
        "target_regimes": md.get("target_regimes") or [],
        "engines": engines,
        "lanes": lanes,
        "champions": champions_out,
        "recent_results": md.get("recent_results") or [],
        "rejection_summary": md.get("rejection_summary") or {},
        "errors": raw.get("errors") or [],
        "warnings": raw.get("warnings") or []
    }


def placeholder_bot(bot_id: str, bot_cfg: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "id": bot_id,
        "display_name": bot_cfg.get("display_name", bot_id),
        "kind": bot_cfg.get("kind", "unknown"),
        "available": False,
        "status": "placeholder",
        "notes": [reason],
        "current_run": "In progress",
        "current_goal": "Placeholder reserved for future status integration.",
        "estimated_apr": None,
        "champions": [],
        "engines": [],
        "lanes": [],
        "recent_results": [],
        "errors": [],
        "warnings": []
    }


def normalize_generic(bot_id: str, bot_cfg: Dict[str, Any], raw: Dict[str, Any], source_path: Path, stale_after_seconds: int) -> Dict[str, Any]:
    status, notes = determine_running(raw, source_path, stale_after_seconds)
    return {
        "id": bot_id,
        "display_name": bot_cfg.get("display_name", bot_id),
        "kind": bot_cfg.get("kind", "unknown"),
        "available": True,
        "status": status,
        "notes": notes,
        "source_path": str(source_path),
        "source_updated_at": raw.get("updated_at"),
        "app": raw.get("app", bot_cfg.get("display_name", bot_id)),
        "version": raw.get("version", ""),
        "current_run": raw.get("mode") or raw.get("phase") or "Unknown",
        "current_goal": raw.get("message") or "Status file loaded.",
        "estimated_apr": best_number(raw.get("estimated_apr"), raw.get("apr"), raw.get("current_apr"), default=None, decimals=4),
        "raw": raw,
        "champions": [],
        "engines": [],
        "lanes": [],
        "recent_results": [],
        "errors": raw.get("errors") or [],
        "warnings": raw.get("warnings") or []
    }


def build_combined_status(config: Dict[str, Any]) -> Dict[str, Any]:
    stale_after = int(config.get("update", {}).get("stale_after_seconds", 900))
    bots_cfg = config.get("bots", {})
    bots: Dict[str, Any] = {}
    warnings: List[str] = []
    errors: List[str] = []

    for bot_id, bot_cfg in bots_cfg.items():
        if not bot_cfg.get("enabled", True):
            continue

        source_path = Path(os.path.expandvars(bot_cfg.get("status_path", "")))
        raw, err = load_json(source_path)

        if raw is None:
            reason = err or "Status file unavailable."
            warnings.append(f"{bot_id}: {reason}")
            bots[bot_id] = placeholder_bot(bot_id, bot_cfg, reason)
            continue

        if bot_id == "profit_monkey":
            bots[bot_id] = normalize_monkey(raw, source_path, stale_after)
        else:
            bots[bot_id] = normalize_generic(bot_id, bot_cfg, raw, source_path, stale_after)

    monkey = bots.get("profit_monkey", {})
    summary = {
        "available_bots": sum(1 for b in bots.values() if b.get("available")),
        "configured_bots": len(bots),
        "running_bots": sum(1 for b in bots.values() if b.get("status") == "running"),
        "best_current_apr_bot": None,
        "profit_monkey_estimated_apr": monkey.get("estimated_apr"),
        "profit_monkey_status": monkey.get("status"),
        "profit_monkey_current_run": monkey.get("current_run")
    }

    best_id = None
    best_apr = None
    for bot_id, bot in bots.items():
        apr = bot.get("estimated_apr")
        if apr is None:
            continue
        try:
            apr_f = float(apr)
        except Exception:
            continue
        if best_apr is None or apr_f > best_apr:
            best_apr = apr_f
            best_id = bot_id

    if best_id:
        summary["best_current_apr_bot"] = {
            "id": best_id,
            "display_name": bots[best_id].get("display_name"),
            "estimated_apr": best_apr
        }

    return {
        "schema": "allbots_status_1_0_0",
        "generated_at": iso_utc(),
        "generator": {
            "app": "profit-github github_update.py",
            "version": APP_VERSION
        },
        "summary": summary,
        "bots": bots,
        "warnings": warnings,
        "errors": errors
    }


def run_cmd(cmd: List[str], cwd: Path) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False
        )
        return p.returncode, p.stdout.strip()
    except Exception as exc:
        return 999, str(exc)


def ensure_git_repo(repo_dir: Path, cfg: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    gh = cfg.get("github", {})
    repo_url = gh.get("repo_url")
    branch = gh.get("branch", "main")
    remote_name = gh.get("remote_name", "origin")

    repo_dir.mkdir(parents=True, exist_ok=True)

    if not (repo_dir / ".git").exists():
        notes.append("No .git folder found. Initializing local Git repo.")
        code, out = run_cmd(["git", "init", "-b", branch], repo_dir)
        if code != 0:
            notes.append(f"git init -b failed, trying older git init path: {out}")
            code, out = run_cmd(["git", "init"], repo_dir)
            notes.append(out)
            run_cmd(["git", "checkout", "-B", branch], repo_dir)
        else:
            notes.append(out)

    code, out = run_cmd(["git", "remote", "get-url", remote_name], repo_dir)
    if code != 0 and repo_url:
        code2, out2 = run_cmd(["git", "remote", "add", remote_name, repo_url], repo_dir)
        notes.append(out2 or f"Added remote {remote_name}.")
    elif repo_url and out.strip() != repo_url:
        notes.append(f"Remote {remote_name} currently points to {out}. Leaving it unchanged.")

    return notes


def git_commit_push(repo_dir: Path, cfg: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    gh = cfg.get("github", {})
    branch = gh.get("branch", "main")
    remote_name = gh.get("remote_name", "origin")
    commit_message = gh.get("commit_message", "Update allbots status")
    push_enabled = bool(gh.get("push_enabled", True))

    run_cmd(["git", "add", "-A"], repo_dir)
    code, status_out = run_cmd(["git", "status", "--porcelain"], repo_dir)
    if code != 0:
        notes.append(f"git status failed: {status_out}")
        return notes

    if not status_out.strip():
        notes.append("No Git changes to commit.")
        return notes

    code, out = run_cmd(["git", "commit", "-m", commit_message], repo_dir)
    if code != 0:
        notes.append(f"git commit failed: {out}")
        return notes
    notes.append(out)

    if push_enabled:
        code, out = run_cmd(["git", "push", "-u", remote_name, branch], repo_dir)
        if code != 0:
            notes.append(f"git push failed: {out}")
        else:
            notes.append(out)
    else:
        notes.append("Push disabled in config.")

    return notes


def load_config(config_path: Path) -> Dict[str, Any]:
    raw, err = load_json(config_path)
    if raw is None:
        raise SystemExit(f"Could not load config: {err}")
    return raw


def one_cycle(config_path: Path, no_push: bool = False) -> int:
    cfg = load_config(config_path)

    repo_dir = Path(os.path.expandvars(cfg.get("paths", {}).get("local_repo_dir", ".")))
    combined_rel = cfg.get("paths", {}).get("combined_status_relative_path", r"data\status.json")
    combined_path = repo_dir / combined_rel

    git_notes = ensure_git_repo(repo_dir, cfg)

    combined = build_combined_status(cfg)
    if git_notes:
        combined.setdefault("warnings", []).extend(git_notes)

    pretty = bool(cfg.get("update", {}).get("write_pretty_json", True))
    write_json(combined_path, combined, pretty=pretty)

    print(f"[{iso_utc()}] Wrote {combined_path}")
    print(f"  Profit Monkey status: {combined.get('summary', {}).get('profit_monkey_status')}")
    print(f"  Profit Monkey APR: {combined.get('summary', {}).get('profit_monkey_estimated_apr')}")

    if no_push:
        print("  Skipped Git push because --no-push was used.")
        return 0

    notes = git_commit_push(repo_dir, cfg)
    for note in notes:
        if note:
            print("  " + note.replace("\n", "\n  "))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine bot status files and update GitHub Pages.")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--once", action="store_true", help="Run one update cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run forever, updating every loop_seconds")
    parser.add_argument("--no-push", action="store_true", help="Write data/status.json but do not git commit/push")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    cfg = load_config(config_path)
    loop_seconds = int(cfg.get("update", {}).get("loop_seconds", 300))

    if args.loop:
        print(f"Profit GitHub updater v{APP_VERSION}")
        print(f"Updating every {loop_seconds} seconds. Press Ctrl+C to stop.")
        while True:
            try:
                one_cycle(config_path, no_push=args.no_push)
            except KeyboardInterrupt:
                print("Stopped.")
                return 0
            except Exception as exc:
                print(f"[{iso_utc()}] ERROR: {exc}")
            time.sleep(loop_seconds)

    return one_cycle(config_path, no_push=args.no_push)


if __name__ == "__main__":
    raise SystemExit(main())
