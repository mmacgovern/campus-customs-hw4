export default function About() {
  return (
    <article className="about">
      <header className="page-header">
        <p className="eyebrow">Our story</p>
        <h1>About Us</h1>
      </header>
      <div className="about-grid">
        <div className="about-body">
          <p className="about-lede">
            Campus Customs is a family-run New Haven shop that has been dressing the Yale community
            since the 1970s.
          </p>
          <p>
            Our storefront sits on Broadway, right across from campus, so students can stop in
            between classes and visitors can grab a souvenir on their way through town.
          </p>
          <p>
            We started as a printing shop, and that's still at the heart of what we do. We handle
            screen printing, embroidery and design in-house, which means we can turn out custom
            pieces for teams, clubs, reunions and events, including gear printed with your own
            class year.
          </p>
          <blockquote className="pull-quote">
            Easy comfort, Yale pride, and a shop that knows the campus.
          </blockquote>
          <p>
            Our Bulldog Blue line is all about navy-and-white staples, residential college designs,
            varsity sports logos and rivalry-week shirts for The Game.
          </p>
        </div>
        <aside className="info-card">
          <h2>Visit us</h2>
          <p>
            <strong>57 Broadway</strong>
            <br />
            New Haven, CT 06511
          </p>
          <h3>In-house services</h3>
          <ul>
            <li>Screen printing</li>
            <li>Embroidery</li>
            <li>Graphic design</li>
            <li>Custom class-year gear</li>
          </ul>
        </aside>
      </div>
    </article>
  )
}
