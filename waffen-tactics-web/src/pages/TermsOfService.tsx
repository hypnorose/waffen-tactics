export default function TermsOfService() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="card">
        <h1 className="text-4xl font-bold text-primary mb-6">📜 Regulamin Usługi</h1>
        
        <div className="space-y-6 text-text/90">
          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">1. Postanowienia ogólne</h2>
            <p>
              Waffen Tactics to darmowa gra strategiczna typu auto-battler dostępna poprzez Discord oraz przeglądarkę internetową.
              Korzystając z usługi, akceptujesz niniejszy regulamin.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">2. Warunki korzystania</h2>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Użytkownik musi posiadać aktywne konto Discord</li>
              <li>Zabronione jest używanie botów, automatyzacji lub exploitów</li>
              <li>Zabraniamy obraźliwych nazw użytkowników i treści</li>
              <li>Konta mogą być usunięte za naruszenie regulaminu</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">3. Prywatność i dane</h2>
            <p className="mb-2">Zbieramy i przechowujemy:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Discord User ID (identyfikator użytkownika)</li>
              <li>Nick Discord (wyświetlany w grze)</li>
              <li>Postęp w grze (poziom, jednostki, statystyki)</li>
            </ul>
            <p className="mt-3">
              Nie udostępniamy danych osobowych osobom trzecim. Dane są używane wyłącznie do funkcjonowania gry.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">4. Autoryzacja Discord OAuth</h2>
            <p>
              Logowanie poprzez Discord OAuth wymaga zgody na dostęp do podstawowych informacji profilu (scope: identify).
              Nie mamy dostępu do prywatnych wiadomości ani serwerów.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">5. Odpowiedzialność</h2>
            <p>
              Gra jest dostarczana "tak jak jest" (AS IS). Nie gwarantujemy ciągłości działania usługi.
              Nie ponosimy odpowiedzialności za utratę postępu w wyniku błędów technicznych lub resetu bazy danych.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">6. Zmiany w regulaminie</h2>
            <p>
              Zastrzegamy sobie prawo do wprowadzania zmian w regulaminie w dowolnym momencie.
              Kontynuacja korzystania z usługi oznacza akceptację zmian.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-primary mb-3">7. Kontakt</h2>
            <p>
              W sprawach regulaminu i prywatności skontaktuj się z administratorem poprzez Discord.
            </p>
          </section>

          <div className="mt-8 pt-6 border-t border-primary/20 text-sm text-text/60">
            <p>Ostatnia aktualizacja: 12 grudnia 2024</p>
            <p>Waffen Tactics - Fan Project</p>
          </div>
        </div>
      </div>
    </div>
  )
}
