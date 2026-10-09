# Claude Code opzetten voor de triage

Doel: Claude in je terminal/app die de scanner draait én zelf de meldingen
uitdunt tot de 1-2 die echt tellen. Makkelijkste route = de desktop-app (die
bevat Claude Code; geen Node.js of CLI-gedoe nodig).

> Let op: Claude Code zit in een **betaald** plan (Pro, Max, Team of
> Enterprise). Het gratis plan heeft het niet.

---

## Stap 1 — App installeren

1. Ga naar **claude.com/download**
2. Download de versie voor macOS (werkt op Intel én Apple Silicon)
3. Open het installer-bestand, sleep Claude naar je Programma's/Applications
4. Start Claude en log in met je account

## Stap 2 — De Code-tab openen

1. Open de Claude-app
2. Klik bovenin op de tab **Code**
3. Klik op **+ New session** (of druk Cmd+N)

## Stap 3 — De juiste map kiezen

Je wil dat Claude Code in de map met **de scanner + de repo die je wil checken**
werkt. Simpelste opzet: zet de te scannen repo náást de `solscan`-map, of laat
Claude 'm zelf clonen (dat kan 'ie).

- Kies bij de nieuwe sessie je **`solscan`-map** als projectmap.
- Claude Code leest dan automatisch het `CLAUDE.md`-bestand dat erin staat, en
  weet meteen hoe de scanner werkt en wat de triage-taak is.

## Stap 4 — De opdracht plakken

Plak dit in Claude Code om de hele Reflect-analyse in één keer te laten doen:

```
Clone https://github.com/donjne/reflect-program-library en draai er
python3 scan.py --github ... op (of scan de lokale map als je 'm al hebt).
Negeer alles onder cli/, client/, sdk/ en scripts/ — dat is geen on-chain code.
Kijk alleen naar program/src/ en instructions/.

Loop daarna elke overgebleven HIGH- en MEDIUM-melding één voor één na, lees de
code eromheen, en beoordeel per stuk: kan deze waarde realistisch overlopen of
door een aanvaller gestuurd worden, én zit er geld of autoriteit aan vast?

Geef me op het eind een korte lijst van alleen de echte kandidaten: per stuk
het bestand:regelnummer, waarom het misbruikt kan worden, en zo mogelijk een
concrete invoer die het breekt. Schrijf geen exploit — alleen de analyse.
```

## Stap 5 — Verifiëren vóór je iemand mailt

Als er een echte kandidaat uitkomt: check eerst of de code ook écht live staat.
Pak de `declare_id!("...")` uit het bestaande programma, plak die Program ID in
Solscan.io, en kijk of 'ie als actief programma op mainnet draait. Zo niet →
het is een testrepo, niks mee doen.

---

## Samengevat

1. App van claude.com/download → inloggen
2. Code-tab → New session → kies je `solscan`-map
3. Plak de opdracht uit stap 4
4. Claude draait de scanner + doet de triage
5. Jij verifieert de echte kandidaat op Solscan vóór contact

Het `CLAUDE.md`-bestand in de map zorgt dat Claude Code de regels al kent:
alleen detecteren (geen exploits), alleen publieke code, gratis en netjes
melden.
