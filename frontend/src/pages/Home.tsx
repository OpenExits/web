import { Link } from "react-router";
import { useTranslation } from "react-i18next";

function Arrow({ color = "#ffffff" }: { color?: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M2 8 H13 M9 3.5 L13.5 8 L9 12.5"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Home() {
  const { t } = useTranslation(["home", "common"]);
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-granite px-6 py-20 text-paper lg:px-16 lg:py-24">
        <svg
          className="pointer-events-none absolute -top-10 right-0 opacity-50"
          width="900"
          height="620"
          viewBox="0 0 900 620"
          fill="none"
          aria-hidden
        >
          <path d="M60 560 C 220 480, 260 380, 430 350 C 610 318, 660 200, 850 170" stroke="#2b2f35" strokeWidth="1.5" />
          <path d="M20 500 C 200 430, 280 330, 460 300 C 640 270, 700 150, 890 120" stroke="#2b2f35" strokeWidth="1.5" />
          <path d="M-10 440 C 190 380, 300 280, 490 250 C 670 222, 740 100, 920 70" stroke="#31363d" strokeWidth="1.5" />
          <path d="M-30 380 C 180 330, 330 230, 520 200 C 700 172, 780 60, 950 20" stroke="#31363d" strokeWidth="1.5" />
          <circle cx="520" cy="200" r="5" fill="#e84e10" />
        </svg>
        <div className="relative flex max-w-3xl flex-col gap-7">
          <span className="font-mono text-[13px] tracking-[0.14em] text-signal">
            {t("home:hero.kicker")}
          </span>
          <h1 className="font-display text-4xl leading-[1.05] lg:text-6xl">{t("home:hero.title")}</h1>
          <p className="max-w-2xl text-lg leading-relaxed text-[#b8bcb4]">{t("home:hero.sub")}</p>
          <div className="mt-2 flex flex-wrap gap-4">
            <Link
              to="/map"
              className="flex items-center gap-2.5 rounded bg-signal px-6 py-3.5 font-bold text-white"
            >
              {t("home:hero.ctaMap")}
              <Arrow />
            </Link>
            <Link
              to="/docs"
              className="rounded border-[1.5px] border-[#4a4f56] px-6 py-3.5 font-semibold text-paper"
            >
              {t("home:hero.ctaSpec")}
            </Link>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="flex flex-col gap-10 border-b border-line px-6 py-16 lg:flex-row lg:gap-16 lg:px-16">
        <div className="flex flex-1 flex-col gap-4">
          <h2 className="font-display text-3xl leading-tight">{t("home:problem.title")}</h2>
          <p className="max-w-xl leading-relaxed text-[#4a4c46]">{t("home:problem.body")}</p>
        </div>
        <div className="flex w-full flex-col gap-2.5 rounded-md bg-ink p-7 font-mono text-sm text-[#b8bcb4] lg:w-[420px]">
          <span className="text-muted">{t("home:problem.codeCommentBad")}</span>
          <span>
            "height": <span className="text-[#e8b34b]">722</span>,
          </span>
          <span>
            "heightValue": <span className="text-[#e8b34b]">2369</span>,
          </span>
          <span className="mt-1.5 border-t border-granite-2 pt-3 text-muted">
            {t("home:problem.codeCommentGood")}
          </span>
          <span>
            "rockdrop": {"{"} "valueM": <span className="text-[#7fc98a]">220</span>,
          </span>
          <span className="pl-4">
            "method": <span className="text-[#9ecbde]">"laser"</span>, "measuredAt":{" "}
            <span className="text-[#9ecbde]">"2026-05-14"</span> {"}"}
          </span>
        </div>
      </section>

      {/* Pillars */}
      <section className="flex flex-col gap-10 px-6 py-16 lg:px-16">
        <h2 className="font-display text-3xl">{t("home:pillars.title")}</h2>
        <div className="grid gap-7 md:grid-cols-3">
          {(["standard", "commons", "foundation"] as const).map((key) => (
            <div key={key} className="flex flex-col gap-3.5 rounded-md border border-line bg-white p-7">
              <h3 className="text-lg font-bold">{t(`home:pillars.${key}.title`)}</h3>
              <p className="text-[15px] leading-relaxed text-[#4a4c46]">
                {t(`home:pillars.${key}.body`)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Three locks */}
      <section className="flex flex-col gap-10 bg-ink px-6 py-16 text-paper lg:px-16">
        <div className="flex flex-col gap-3">
          <h2 className="font-display text-3xl">{t("home:locks.title")}</h2>
          <p className="text-ondark-muted">{t("home:locks.sub")}</p>
        </div>
        <div className="grid gap-7 md:grid-cols-3">
          {(["lock1", "lock2", "lock3"] as const).map((key, i) => (
            <div key={key} className="flex flex-col gap-3 rounded-md border border-granite-2 p-6">
              <span className="font-mono text-[13px] text-signal">LOCK 0{i + 1}</span>
              <h3 className="text-lg font-bold">{t(`home:locks.${key}.title`)}</h3>
              <p className="text-[15px] leading-relaxed text-[#b8bcb4]">
                {t(`home:locks.${key}.body`)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Contribute */}
      <section className="flex flex-col items-start gap-12 border-b border-line px-6 py-16 lg:flex-row lg:items-center lg:justify-between lg:px-16">
        <div className="flex max-w-2xl flex-col gap-4">
          <h2 className="font-display text-3xl leading-tight">{t("home:contribute.title")}</h2>
          <p className="leading-relaxed text-[#4a4c46]">{t("home:contribute.body")}</p>
          <div className="mt-1 flex items-center gap-5">
            <Link to="/panel" className="rounded bg-ink px-6 py-3 font-bold text-paper">
              {t("home:contribute.cta")}
            </Link>
            <span className="flex items-center gap-2 text-sm font-semibold">
              {t("home:contribute.ctaAlt")}
              <Arrow color="#1a1c1e" />
            </span>
          </div>
        </div>
        <div className="flex w-full flex-col gap-2.5 rounded-md border border-line bg-white px-7 py-6 lg:w-[380px]">
          <span className="font-mono text-xs tracking-[0.1em] text-muted">
            {t("home:contribute.steps.kicker")}
          </span>
          {(["s1", "s2", "s3"] as const).map((key, i) => (
            <span key={key} className="flex items-center gap-2.5 text-sm">
              <span className="flex h-[22px] w-[22px] items-center justify-center rounded-full bg-signal text-xs font-bold text-white">
                {i + 1}
              </span>
              {t(`home:contribute.steps.${key}`)}
            </span>
          ))}
        </div>
      </section>

      {/* Safety notice (rule OE-R09) */}
      <section className="flex items-center gap-4 bg-warnbg px-6 py-7 lg:px-16">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="shrink-0" aria-hidden>
          <path d="M12 3 L22 20 H2 Z" stroke="#8a5a0a" strokeWidth="2" strokeLinejoin="round" />
          <path d="M12 10 V14.5" stroke="#8a5a0a" strokeWidth="2" strokeLinecap="round" />
          <circle cx="12" cy="17.2" r="1.2" fill="#8a5a0a" />
        </svg>
        <p className="max-w-4xl text-sm leading-relaxed text-warntext">
          <strong>{t("common:safety.title")}</strong> {t("common:safety.body")}
        </p>
      </section>
    </div>
  );
}
