"""Verify TOU tariff differences between Decision 963 and Decision 14 regimes."""
import json
from pathlib import Path

BASE = Path("artifacts/results/tou_comparison")

SCENARIOS = {
    "saigon18": {
        "963": BASE / "2026-03-20-scenario-a-fixed-sizing-evntou" / "699155b878151af0" / "input.json",
        "14": BASE / "2026-03-20-scenario-a-fixed-sizing-evntou" / "a41f7a6f42f74a15" / "input.json",
    },
    "ninhsim": {
        "963": BASE / "2026-04-01-ninhsim-scenario-a-baseline-evn" / "2e8fe0e9c75b512e" / "input.json",
        "14": BASE / "2026-04-01-ninhsim-scenario-a-baseline-evn" / "4197f09595c116bf" / "input.json",
    },
    "north_thuan": {
        "963": BASE / "north-thuan-scenario-a" / "7b6088d3bcaf7eae" / "input.json",
        "14": BASE / "north-thuan-scenario-a" / "8b0ea70a863bf48a" / "input.json",
    },
}

all_pass = True
for name, paths in SCENARIOS.items():
    d963 = json.loads(paths["963"].read_text())
    d14 = json.loads(paths["14"].read_text())
    rates_963 = d963["ElectricTariff"]["tou_energy_rates_per_kwh"]
    rates_14 = d14["ElectricTariff"]["tou_energy_rates_per_kwh"]

    diffs = sum(1 for a, b in zip(rates_963, rates_14) if abs(a - b) > 1e-10)
    m963 = rates_963[0:24]
    m14 = rates_14[0:24]
    peak_963 = [h for h in range(24) if m963[h] == max(m963)]
    peak_14 = [h for h in range(24) if m14[h] == max(m14)]

    print(f"\n=== {name} ===")
    print(f"  Hours with different rates: {diffs}/8760")
    print(f"  Decision 963 peak hours (Mon): {peak_963}")
    print(f"  Decision 14 peak hours (Mon): {peak_14}")

    ok = True
    if peak_963 != [17, 18, 19, 20, 21, 22]:
        print(f"  FAIL: Decision 963 peak hours wrong: {peak_963}")
        ok = False
    if peak_14 != [9, 10, 17, 18, 19]:
        print(f"  FAIL: Decision 14 peak hours wrong: {peak_14}")
        ok = False
    if diffs == 0:
        print("  FAIL: No rate differences between regimes")
        ok = False
    if ok:
        print("  PASS: All assertions correct")
    else:
        all_pass = False

print(f"\n{'=== ALL SCENARIOS VERIFIED ===' if all_pass else '=== SOME SCENARIOS FAILED ==='}")
