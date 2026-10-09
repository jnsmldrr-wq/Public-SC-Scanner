# Triage: Aurus (EVM, batch 2)

- Adres: `0xe4a6f23fb9e00fca037aa0ea0a6954de0a6c53bf` = `TransparentUpgradeableProxy` (0.8.2).
- Implementation: `0xbaf1151c576097302f0300aa8fbd6ff312babef6` = **TokenizedGold** (0.8.4), bevestigd via de EIP-1967-slot.
- Fork? Nee. Eigen token-logica (goud-gedekte ERC-20 met whitelist-niveaus en transfer-fees) bovenop OZ `ERC20PausableUpgradeable`.
- Datum: 2026-10-05. Read-only.

**Scan:** High 1 (67 dependency-findings weggefilterd). Ruwe output: `evm-reports/batch2/aurus.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `shadowing-state` `TokenizedGold._balances` (`TokenizedGold.sol:41`) | n.v.t. | Gedeclareerd maar **nergens gebruikt**: een dood slot. De `_transfer`-override (`:150`) loopt via `super._transfer`, dus de OZ-boekhouding blijft leidend. |

**Notitie (LAAG):**
- De transfer-fee wordt naar beneden afgerond (`mul` → `div`). Dat is verwaarloosbaar.
- Fee-tarieven, whitelist en mint zijn owner/minter-only.
