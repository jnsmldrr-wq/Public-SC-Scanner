# SolScan uitleg (voor een 12-jarige)

## Wat is dit ding eigenlijk?

Stel je voor: iemand schrijft een rekenmachine die met **echt geld** werkt.
Jij typt erin "geef mij 10 munten" en de machine doet dat. Zo'n machine op de
Solana-blockchain heet een **program**.

Maar soms zit er een foutje in die machine. Bijvoorbeeld: je kunt "geef mij
−5 munten" intypen en dan geeft hij je per ongeluk een miljoen munten. Dat is
een **bug**, en bij geld-machines kan dat heel duur zijn.

**SolScan is je speurhond.** Je laat hem de code van zo'n machine snuffelen, en
hij blaft op de plekken die er verdacht uitzien: "Hé, hier klopt de rekensom
niet!" of "Hé, iedereen mag hier zomaar geld pakken!"

Hij **repareert niks** en hij **steelt niks**. Hij wijst alleen aan. Net als een
rookmelder: die blust het vuur niet, hij piept zodat jíj iets kunt doen.

---

## Wat heb je nodig?

1. Een computer met **Python** erop (versie 3.10 of nieuwer).
2. De map `solscan` die we gemaakt hebben.

Dat is het. Geen ingewikkelde installatie, geen extra spullen downloaden.

---

## Hoe start je 'm? (3 stapjes)

**Stap 1 — open de map.**
Open het programma "Terminal" (dat is een zwart venster waarin je typt) en ga
naar de map:

```
cd pad/naar/solscan
```

(`cd` betekent gewoon "ga naar deze map".)

**Stap 2 — laat de speurhond snuffelen.**
We hebben een nep-machine met expres-ingebouwde fouten meegeleverd om mee te
oefenen. Laat SolScan die onderzoeken:

```
python scan.py samples/
```

**Stap 3 — lees wat hij gevonden heeft.**
Er verschijnt een lijstje op je scherm. Klaar! Je hebt net je eerste scan
gedaan. 🎉

---

## Hoe lees je wat hij vindt?

Elke vondst krijgt een kleurtje, net als een stoplicht — hoe erger, hoe roder:

| Kleur / woord | Wat het betekent |
|---------------|------------------|
| 🔴 **Critical** | Heel gevaarlijk. Hier moet je echt naar kijken. |
| 🟠 **High** | Belangrijk. Waarschijnlijk een echt probleem. |
| 🟡 **Medium** | Let op, zou een probleem kunnen zijn. |
| 🔵 **Low** | Klein dingetje, niet spannend. |

Bij elke vondst staat ook:
- **welke regel** in de code (bijv. `regel 24`),
- **wat er mis is** in gewone taal,
- en een **tip hoe je het repareert**.

En bijna overal staat erbij: **"verify manually"**. Dat betekent: *"ik denk dat
hier iets fout zit, maar controleer het zelf even voordat je het gelooft."* De
speurhond blaft namelijk soms ook als er niks aan de hand is. Daarom: eerst zelf
kijken, dan pas iemand mailen. Anders lijk je een beetje als het jongetje dat
"WOLF!" riep terwijl er geen wolf was.

---

## Handige trucjes

**Een rapport opslaan** (zodat je het later nog kunt bekijken):

```
python scan.py samples/ --md rapport.md
```

Nu staat alles netjes in een bestandje `rapport.md`.

**Alleen de ergste dingen laten zien** (de kleine dingetjes wegfilteren):

```
python scan.py samples/ --min-severity High
```

**Een machine van internet onderzoeken** (bijvoorbeeld van GitHub):

```
python scan.py --github https://github.com/naam/project
```

Hij haalt de code dan zelf op en snuffelt eraan.

**Een nette mail voorschrijven** naar de eigenaar:

```
python scan.py samples/ --draft-outreach
```

Dan maakt hij alvast een vriendelijk berichtje dat je kunt versturen.

---

## De allerbelangrijkste regel (lees dit!)

Als je een bug vindt bij iemand anders, doe dan het **aardige** ding:

1. **Vertel het ze gewoon, gratis.** "Hoi, ik vond dit, let even op."
2. **Zeg er NIET bij:** "betaal me eerst, anders vertel ik het niet." Dat is
   hetzelfde als iemand bang maken voor geld, en dat mag niet — niet van de
   regels, en niet van de wet.
3. **Ga NOOIT zelf de fout uitproberen** om echt geld weg te halen. Kijken naar
   code mag. Er echt misbruik van maken is stelen.

Daarna mag je rustig vertellen: "ik heb trouwens een programmaatje dat dit soort
fouten automatisch voor je in de gaten houdt" — dát is je bedrijf. Eerst
helpen, daarna pas iets aanbieden. Zo bouw je vertrouwen op, en mensen kopen
veel liever van iemand die ze vertrouwen.

---

## Samengevat in één zin

**SolScan is een rookmelder voor geld-code: hij piept waar het misgaat, jij
beslist wat je ermee doet — en je doet het eerlijk.**
