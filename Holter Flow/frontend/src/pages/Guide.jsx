import { Info, Mail, Calendar, Settings, AlertCircle, MapPin, ArrowLeftRight, LogOut, LogIn, RotateCcw, CalendarPlus, Timer, Activity, CheckCircle, Package } from 'lucide-react';

export default function Guide() {
  return (
    <div className="max-w-4xl mx-auto pb-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">Användarhandbok — Pulsus Holter Tracker</h1>
        <p className="text-slate-500">
          Steg-för-steg guide för hela arbetsflödet: från bokning i Webdoc till att enheten är tillbaka på kliniken.
        </p>
      </div>

      <div className="space-y-6">
        
        {/* ─────────────────────────────────────── */}
        {/* STEG 1: Synkronisering */}
        <Section
          icon={Calendar}
          color="indigo"
          number="1"
          title="Webdoc → Pulsus (Synkronisering)"
        >
          <p>
            Pulsus hämtar automatiskt alla Holter-bokningar från Webdoc. Du kan även göra det manuellt.
          </p>
          <StepList>
            <Step n="1">Gå till <B>Veckoschema</B> i menyn till vänster.</Step>
            <Step n="2">Klicka på knappen <B>Sync Webdoc</B> (uppe till höger).</Step>
            <Step n="3">Systemet hämtar nu alla bokningar med åtgärdskoderna <code className="bg-slate-100 text-indigo-600 px-1.5 py-0.5 rounded text-[11px] font-mono">E1005</code> (24h), <code className="bg-slate-100 text-indigo-600 px-1.5 py-0.5 rounded text-[11px] font-mono">E1006</code> (48h) och <code className="bg-slate-100 text-indigo-600 px-1.5 py-0.5 rounded text-[11px] font-mono">E1007</code> (72h) för de kommande 30 dagarna.</Step>
            <Step n="4">Bokningarna visas i veckoschemats rutnät — en kolumn per enhet, en rad per dag.</Step>
          </StepList>
          <Tip>
            Om en bokning ändras i Webdoc (t.ex. typ ändras från 24h till 48h, eller datum flyttas) uppdateras det automatiskt vid nästa synk.
          </Tip>
          <p className="text-sm">
            Patientens <B>postort</B> hämtas automatiskt och visas med en 📍-ikon, t.ex. <em>FALKENBERG</em> eller <em>VARBERG</em>. Det hjälper dig avgöra om patienten bör returnera enheten via post.
          </p>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 2: Intelligent Bokning */}
        <Section
          icon={CalendarPlus}
          color="purple"
          number="2"
          title="Intelligent Bokning (Boka direkt)"
        >
          <p>
            Om du behöver boka en patient för Holter <B>direkt</B> — utan att gå via Webdoc först — kan du använda <B>Intelligent Bokning</B>.
          </p>
          <StepList>
            <Step n="1">Gå till <B>Veckoschema</B> och klicka på <B>+ Ny bokning</B> (uppe till höger).</Step>
            <Step n="2">Välj undersökningstyp: <B>24h</B>, <B>48h</B> eller <B>72h</B>. Du kan även ange anpassade mätdagar (3–7d).</Step>
            <Step n="3">Klicka <B>Visa lediga tider</B>. Systemet visar alla tillgängliga tider baserat på enheternas aktuella status.</Step>
            <Step n="4">Om en enhet är ledig <B>just nu</B> visas en grön <B>🟢 Nu</B>-slot högst upp med en <B>DIREKT</B>-badge. Klicka på den för att boka omedelbart.</Step>
            <Step n="5">Ange patientens <B>personnummer</B> och klicka <B>Bekräfta Bokning</B>.</Step>
          </StepList>
          <p className="text-sm mt-3">
            Systemet skapar automatiskt:
          </p>
          <ul className="list-none space-y-2 mt-2">
            <StatusRow emoji="📋" label="Pulsus" desc="Lokal bokning skapas omedelbart — enheten reserveras." />
            <StatusRow emoji="🌐" label="Webdoc" desc="Webdoc-bokning skapas automatiskt med rätt bookingType (Holter 24h/48h/72h)." />
          </ul>
          <Tip>
            Om Webdoc-bokningen misslyckas (t.ex. vid API-störning) visas en gul varning. Pulsus-bokningen fungerar fortfarande — du kan skapa Webdoc-bokningen manuellt senare.
          </Tip>
          <Note>
            Tiderna som visas respekterar svensk tid (CET/CEST) och inkluderar alla dagar — även helger.
          </Note>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 3: Checka ut */}
        <Section
          icon={LogOut}
          color="emerald"
          number="3"
          title="Checka ut enhet till patient"
        >
          <p>
            När patienten kommer till kliniken och ska få sin Holter-enhet:
          </p>
          <StepList>
            <Step n="1">Gå till <B>Veckoschema</B> och klicka på patientens bokningskort.</Step>
            <Step n="2">En <B>Bokningsdetaljer</B>-dialog öppnas med all information.</Step>
            <Step n="3">
              Kontrollera att rätt enhet är tilldelad. Om inte — använd <B>Byt Enhet</B>-rutan och klicka <B>Byt</B>.
            </Step>
            <Step n="4">Klicka på den blå knappen <B>Checka ut till patient</B>.</Step>
          </StepList>
          <Important>
            En enhet kan <strong>inte</strong> checkas ut om den redan är på en annan patient. Den måste checkas in först.
          </Important>
          <p className="text-sm">
            Efter utcheckning ändras statusen:
          </p>
          <ul className="list-none space-y-2 mt-2">
            <StatusRow emoji="🟡" label="Bokningen" desc="→ Aktiv (på patient) — pulsande gul prick i schemat" />
            <StatusRow emoji="📦" label="Enheten" desc="→ På patient — visas i Utcheckade-sidan" />
          </ul>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 4: Returmetod */}
        <Section
          icon={Package}
          color="amber"
          number="4"
          title="Välj returmetod (innan utcheckning)"
        >
          <p>
            Innan du checkar ut ska du välja hur patienten ska returnera enheten:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
            <MethodCard
              emoji="🏥"
              title="Fysiskt besök"
              desc="Patienten kommer tillbaka till kliniken och lämnar enheten personligen."
              detail="Standard. Förväntat returdatum = utcheckningsdatum + mätdagar."
            />
            <MethodCard
              emoji="📮"
              title="Postretur"
              desc="Patienten skickar tillbaka enheten med posten."
              detail="Returdatum = utcheckningsdatum + mätdagar + 3 vardagar (posttransit)."
            />
          </div>
          <Tip>
            Du växlar returmetod i bokningsmodalen under <B>Returmetod</B> — klicka antingen "Fysiskt besök" eller "Postretur" innan du checkar ut.
          </Tip>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 5: Mätdagar (72h+) */}
        <Section
          icon={Timer}
          color="blue"
          number="5"
          title="Anpassa mätdagar (72h-bokningar)"
        >
          <p>
            Ibland behöver patienten bära enheten längre än 3 dagar — upp till 7 dagar. I Webdoc bokas detta alltid som <B>Holter 72h</B>, men i Pulsus kan du ange exakt antal dagar.
          </p>
          <StepList>
            <Step n="1">Öppna en bokning som har typ <B>Holter 72h</B> i Veckoschemat.</Step>
            <Step n="2">Under <B>Mätdagar (72h+)</B> visas knappar: <B>3d  4d  5d  6d  7d</B>.</Step>
            <Step n="3">Klicka på rätt antal dagar. Systemet sparar direkt.</Step>
          </StepList>
          <p className="text-sm">
            Längst ned visas alltid: <em>"Webdoc-typ: Holter 72h · Faktisk mätning: 5 dagar"</em> — så att det är tydligt vad som gäller.
          </p>
          <Note>
            24h- och 48h-bokningar har fast mätlängd (1 resp. 2 dagar) och visar ingen mätdagar-väljare.
          </Note>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 6: Checka in */}
        <Section
          icon={LogIn}
          color="emerald"
          number="6"
          title="Checka in enhet (patienten returnerar)"
        >
          <p>
            När patienten lämnar tillbaka enheten — antingen personligen eller via post — ska du checka in den i systemet.
          </p>
          
          <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">Alternativ A: Via bokningsmodalen</h3>
          <StepList>
            <Step n="1">Gå till <B>Veckoschema</B> och klicka på bokningskortet (gul pulsande prick).</Step>
            <Step n="2">Klicka på den gröna knappen <B>Checka in enhet (returnerad)</B>.</Step>
          </StepList>
          
          <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">Alternativ B: Via Utcheckade-sidan</h3>
          <StepList>
            <Step n="1">Gå till <B>Utcheckade</B> i menyn.</Step>
            <Step n="2">Hitta rätt patient i listan.</Step>
            <Step n="3">Klicka på den gröna <B>Checka in</B>-knappen till höger.</Step>
          </StepList>

          <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">Alternativ C: Via Posthantering (postretur)</h3>
          <StepList>
            <Step n="1">Gå till <B>Posthantering</B> i menyn.</Step>
            <Step n="2">Klicka <B>Checka in (mottagen)</B> när enheten anländer med posten.</Step>
          </StepList>

          <p className="text-sm mt-3">
            Efter incheckning:
          </p>
          <ul className="list-none space-y-2 mt-2">
            <StatusRow emoji="🟢" label="Bokningen" desc="→ Klar — grön prick i schemat" />
            <StatusRow emoji="✅" label="Enheten" desc="→ Tillgänglig — kan tilldelas nästa patient" />
          </ul>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 7: Skjuta upp */}
        <Section
          icon={CalendarPlus}
          color="amber"
          number="7"
          title="Skjut upp inlämning (försenad patient)"
        >
          <p>
            Ibland kan patienten inte returnera enheten i tid. Då kan du skjuta upp det förväntade returdatumet.
          </p>
          
          <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">Via bokningsmodalen (Veckoschema)</h3>
          <StepList>
            <Step n="1">Klicka på en <B>aktiv</B> bokning (gul pulsande prick).</Step>
            <Step n="2">Under "Skjut upp inlämning" visas en <B>kalender</B>.</Step>
            <Step n="3">Välj nytt returdatum genom att klicka på en dag.</Step>
            <Step n="4">Klicka <B>Bekräfta nytt datum</B>.</Step>
          </StepList>

          <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">Via Utcheckade-sidan</h3>
          <StepList>
            <Step n="1">Gå till <B>Utcheckade</B> i menyn.</Step>
            <Step n="2">Klicka <B>Skjut upp</B> bredvid rätt patient.</Step>
            <Step n="3">En kalender öppnas inline — välj nytt datum.</Step>
            <Step n="4">Klicka <B>Bekräfta</B>.</Step>
          </StepList>
          <Note>
            Du kan inte välja ett datum i det förflutna. Nuvarande returdatum visas ovanför kalendern.
          </Note>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 8: Reaktivera */}
        <Section
          icon={RotateCcw}
          color="orange"
          number="8"
          title="Reaktivera en bokning (ångra incheckning)"
        >
          <p>
            Om en bokning av misstag markerats som klar kan du återställa den.
          </p>
          <StepList>
            <Step n="1">Klicka på en bokning med <B>Klar</B>-status i Veckoschemat.</Step>
            <Step n="2">Klicka på den gula knappen <B>Reaktivera bokning</B>.</Step>
            <Step n="3">Bokningen återgår till <B>Schemalagd</B> — alla tidsdata nollställs.</Step>
          </StepList>
          <Warning>
            Reaktivering tar bort alla tidsstämplar (utcheckad, incheckad). Enheten markeras som tillgänglig.
          </Warning>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* STEG 9: Byta enhet */}
        <Section
          icon={ArrowLeftRight}
          color="purple"
          number="9"
          title="Byta enhet (omtilldelning)"
        >
          <p>
            Om en patient behöver byta till en annan fysisk enhet:
          </p>
          <StepList>
            <Step n="1">Klicka på bokningen i Veckoschemat.</Step>
            <Step n="2">Under <B>Byt Enhet</B> välj den nya enheten i rullistan.</Step>
            <Step n="3">Klicka <B>Byt</B>.</Step>
          </StepList>
          <Tip>
            Om den nya enheten redan har en patient under samma period sker ett automatiskt <B>byte</B> — den andra patienten flyttas till den gamla enheten. Systemet hanterar detta automatiskt.
          </Tip>
        </Section>

        {/* ─────────────────────────────────────── */}
        {/* Sidöversikt */}
        <div className="card p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 rounded-xl bg-slate-100 text-slate-600">
              <Info size={24} />
            </div>
            <h2 className="text-lg font-semibold text-slate-800">Sidöversikt — Vad hittar jag var?</h2>
          </div>
          <div className="overflow-x-auto ml-16">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-[11px] text-slate-400 uppercase tracking-wider">
                  <th className="pb-2 pr-4 font-medium">Sida</th>
                  <th className="pb-2 pr-4 font-medium">Vad visar den?</th>
                  <th className="pb-2 font-medium">Vanligaste åtgärder</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600">
                <PageRow 
                  page="Dashboard" 
                  desc="Översikt med statistik, aktiva enheter och intäkter" 
                  actions="Snabbgrep på dagens status" 
                />
                <PageRow 
                  page="Veckoschema" 
                  desc="Kalendervy: alla bokningar per enhet och dag" 
                  actions="Synk, checka ut/in, byt enhet, ändra mätdagar, returmetod" 
                />
                <PageRow 
                  page="Enhetsregister" 
                  desc="Lista på alla fysiska enheter och deras status" 
                  actions="Lägga till / ta bort enheter" 
                />
                <PageRow 
                  page="Posthantering" 
                  desc="Spåra enheter som returneras via post" 
                  actions="Checka in mottagna postenheter" 
                />
                <PageRow 
                  page="Utcheckade" 
                  desc="Alla enheter som är på patient just nu" 
                  actions="Checka in, skjut upp returdatum" 
                />
              </tbody>
            </table>
          </div>
        </div>

        {/* Status-vokabulär */}
        <div className="card p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 rounded-xl bg-slate-100 text-slate-600">
              <Activity size={24} />
            </div>
            <h2 className="text-lg font-semibold text-slate-800">Statusar — Vad betyder de?</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 ml-16">
            <StatusCard color="bg-slate-100 text-slate-600 border-slate-200" label="Schemalagd" desc="Bokningen finns men enheten är inte utlämnad ännu." />
            <StatusCard color="bg-amber-50 text-amber-700 border-amber-200" label="Aktiv (på patient)" desc="Enheten är utcheckad — patienten bär den." />
            <StatusCard color="bg-emerald-50 text-emerald-700 border-emerald-200" label="Klar" desc="Enheten returnerad. Bokningen är avslutad." />
            <StatusCard color="bg-red-50 text-red-600 border-red-200" label="Försenad" desc="Enheten har passerat förväntat returdatum." />
          </div>
        </div>

      </div>

      {/* Copyright Footer */}
      <div className="mt-12 pt-6 border-t border-slate-200 text-center">
        <p className="text-xs text-slate-400">
          © {new Date().getFullYear()} Hjärtcentrum Halland. Alla rättigheter förbehållna.
        </p>
        <p className="text-[10px] text-slate-300 mt-1">Pulsus Holter Tracker v2.1</p>
      </div>
    </div>
  );
}


/* ── Reusable Sub-Components ──────────────────────── */

function Section({ icon: Icon, color, number, title, children }) {
  const bgMap = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    blue: 'bg-blue-50 text-blue-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="card p-6">
      <div className="flex items-center gap-4 mb-4">
        <div className={`p-3 rounded-xl ${bgMap[color] || bgMap.indigo}`}>
          <Icon size={24} />
        </div>
        <h2 className="text-lg font-semibold text-slate-800">{number}. {title}</h2>
      </div>
      <div className="text-slate-600 space-y-3 leading-relaxed ml-16 text-sm">
        {children}
      </div>
    </div>
  );
}

function StepList({ children }) {
  return <ol className="space-y-2 mt-2">{children}</ol>;
}

function Step({ n, children }) {
  return (
    <li className="flex items-start gap-3">
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold flex items-center justify-center mt-0.5">
        {n}
      </span>
      <span>{children}</span>
    </li>
  );
}

function B({ children }) {
  return <span className="text-slate-800 font-semibold">{children}</span>;
}

function Tip({ children }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200 mt-3">
      <CheckCircle size={16} className="text-emerald-600 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-emerald-800">{children}</p>
    </div>
  );
}

function Note({ children }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200 mt-3">
      <Info size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-blue-800">{children}</p>
    </div>
  );
}

function Warning({ children }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-200 mt-3">
      <AlertCircle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-amber-800">{children}</p>
    </div>
  );
}

function Important({ children }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-200 mt-3">
      <AlertCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-red-800">{children}</p>
    </div>
  );
}

function StatusRow({ emoji, label, desc }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span className="text-base">{emoji}</span>
      <span className="text-slate-800 font-medium">{label}</span>
      <span className="text-slate-500">{desc}</span>
    </li>
  );
}

function MethodCard({ emoji, title, desc, detail }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{emoji}</span>
        <span className="text-sm font-semibold text-slate-800">{title}</span>
      </div>
      <p className="text-xs text-slate-600 mb-2">{desc}</p>
      <p className="text-[10px] text-slate-400 italic">{detail}</p>
    </div>
  );
}

function PageRow({ page, desc, actions }) {
  return (
    <tr>
      <td className="py-2.5 pr-4 font-medium text-slate-800">{page}</td>
      <td className="py-2.5 pr-4">{desc}</td>
      <td className="py-2.5 text-slate-500">{actions}</td>
    </tr>
  );
}

function StatusCard({ color, label, desc }) {
  return (
    <div className={`rounded-xl p-3 border ${color}`}>
      <p className="text-xs font-semibold mb-1">{label}</p>
      <p className="text-[10px] opacity-80">{desc}</p>
    </div>
  );
}
