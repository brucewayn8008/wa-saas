export function Manifesto() {
  const items = [
    "FIND PROSPECTS",
    "START CONVERSATIONS",
    "QUALIFY THEM",
    "FOLLOW UP",
    "BOOK MEETINGS",
    "AUTOMATICALLY",
  ];

  return (
    <section
      aria-label="Core loop"
      className="border-b border-line bg-ink text-paper"
    >
      <div className="section-pad mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-6 gap-y-3 py-4">
        {items.map((item, i) => (
          <div key={item} className="flex items-center gap-6">
            <span className="meta text-[10px] tracking-[0.14em] text-paper">
              {item}
            </span>
            {i < items.length - 1 && (
              <span className="hidden text-signal sm:inline" aria-hidden>
                →
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
