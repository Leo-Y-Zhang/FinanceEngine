// Privacy notice for the local question log (`logs/ask.jsonl`).
//
// Compliance context: docs/compliance-review-2026-07-21.md finding #8 flagged
// that free-text questions can contain personal (occasionally special-
// category) data, with no privacy notice. This page is the fix — it is a
// real, linked route (see the "#/privacy" hash route wired in App.tsx), not
// a docs file a user would never see. The 30-day retention figure below is
// enforced server-side by `finance_engine.privacy.retention.purge_expired`.
export function PrivacyNotice() {
  return (
    <main className="shell">
      <header className="masthead">
        <h1 className="wordmark">FinanceEngine</h1>
        <p className="register-line">Privacy notice · last updated 21 July 2026</p>
      </header>

      <a className="back-link" href="#/">
        &larr; Back to FinanceEngine
      </a>

      <h2 className="question-echo">Privacy notice</h2>

      <article className="privacy-notice">
        <p>
          This notice explains what happens to the text of the questions you
          ask FinanceEngine. It is a pre-launch build — not yet a live
          public service — but we want to be straightforward about this from
          the start.
        </p>

        <h2>What we log</h2>
        <p>
          When you ask a question, the server stores three things in a local
          log file (<code>logs/ask.jsonl</code>, kept on the machine running
          FinanceEngine — nothing is sent to any third party, analytics service, or
          cloud store):
        </p>
        <ul>
          <li>the exact text of your question</li>
          <li>the outcome (&ldquo;answer&rdquo;, &ldquo;routing&rdquo;, or &ldquo;abstain&rdquo;)</li>
          <li>the time you asked it</li>
        </ul>
        <p>
          We do not use cookies, accounts, session identifiers, or any
          client-side storage. We do not capture your IP address at the
          application level (the web server software FinanceEngine runs on may
          write your IP to its own transient console/access output,
          separately from the file above — FinanceEngine itself does not read,
          store, or process that).
        </p>
        <p>
          Because questions are free text, they can contain personal data
          even though we never ask for your name or any identifier &mdash;
          for example, &ldquo;I&rsquo;m 45 with a &pound;30,000 SIPP&rdquo;
          describes you without naming you. Occasionally a question could
          touch special-category data under UK GDPR (for example, if it
          mentions a health condition alongside a money question). Please
          avoid including anything you consider especially sensitive if you
          can phrase your question without it &mdash; if it happens anyway,
          the retention and deletion approach below still applies.
        </p>

        <h2>Why we log it</h2>
        <p>We log questions for two purposes, both about the safety and quality of FinanceEngine itself:</p>
        <ol>
          <li>
            To check whether the advice-boundary classifier (the safeguard
            that stops FinanceEngine giving anything that looks like a personal
            recommendation) is working correctly, and to find and fix cases
            it misses.
          </li>
          <li>To improve the accuracy and coverage of answers generally.</li>
        </ol>
        <p>
          We do not use this log for advertising, profiling, or any purpose
          unrelated to building and checking FinanceEngine.
        </p>

        <h2>Our lawful basis</h2>
        <p>
          FinanceEngine is currently a build-only, pre-launch product with no public
          deployment and no real user base &mdash; you are most likely a
          developer, tester, or reviewer rather than a member of the public.
          For that reason, our lawful basis under UK&nbsp;GDPR
          Article&nbsp;6(1)(f) is <strong>legitimate interests</strong>: it is
          necessary and proportionate, while we build and test FinanceEngine, to
          review question logs so we can verify the safety-critical
          classifier is working and improve the product before any real
          launch. There is no consent tick-box because there is currently no
          live, public-facing collection point &mdash; this notice is the
          transparency step for the pre-launch testing that does happen. If
          and when FinanceEngine launches to real members of the public, this basis
          and this notice will be reviewed again as part of the compliance
          sign-off gate that already applies before any launch.
        </p>

        <h2>How long we keep it</h2>
        <p>
          We keep log entries for <strong>30 days</strong> from when they
          were written, then delete them automatically &mdash; entries older
          than 30 days are purged whenever the FinanceEngine server starts. We chose
          30 days because it is enough time to review and act on classifier
          misses, without keeping free-text financial questions any longer
          than needed.
        </p>

        <h2>Your rights</h2>
        <p>Under UK GDPR you have the right to:</p>
        <ul>
          <li>ask what, if anything, of yours is in the log (right of access)</li>
          <li>ask for it to be deleted before the 30-day period is up (right to erasure)</li>
          <li>object to this processing (right to object, since the basis is legitimate interests)</li>
        </ul>
        <p>
          Because the log has no accounts or identifiers, we can only find
          your entry if you can tell us the approximate question text and
          time you asked it.
        </p>

        <h2>Contact</h2>
        <p>
          FinanceEngine does not yet have a public company entity or a monitored
          public contact address &mdash; it is a pre-launch build. Until it
          launches, please raise any privacy question or deletion request
          with <strong>the site operator</strong> through the project&rsquo;s
          private repository. Once FinanceEngine launches for real users, a
          monitored contact address will be published here and this notice
          will be updated accordingly. You also always have the right to
          complain to the UK Information Commissioner&rsquo;s Office
          (<a href="https://ico.org.uk" target="_blank" rel="noopener noreferrer">ico.org.uk</a>)
          regardless of how you contact us.
        </p>
      </article>
    </main>
  );
}

export default PrivacyNotice;
