<?php
/**
 * Sliced Golf — gemeinsame Formular-Logik.
 * Validiert Eingaben, blockt Spam (Honeypot), versendet per mail()
 * an kontakt@slicedgolf.ch und leitet auf /nachricht-gesendet/ weiter.
 */

declare(strict_types=1);

const SG_RECIPIENT = 'kontakt@slicedgolf.ch';
const SG_FROM      = 'no-reply@slicedgolf.ch';

function sg_clean(string $value, int $max = 500): string
{
    // Header-Injection verhindern, Länge begrenzen
    $value = str_replace(["\r", "\n", "%0a", "%0d"], ' ', trim($value));
    return mb_substr($value, 0, $max);
}

function sg_redirect(string $path): void
{
    header('Location: ' . $path, true, 303);
    exit;
}

function sg_handle(string $subject, string $body, string $email, string $backPath): void
{
    $headers = [
        'From: Sliced Golf <' . SG_FROM . '>',
        'Reply-To: ' . $email,
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'X-Mailer: slicedgolf.ch',
    ];

    $ok = @mail(
        SG_RECIPIENT,
        '=?UTF-8?B?' . base64_encode($subject) . '?=',
        $body,
        implode("\r\n", $headers)
    );

    if ($ok) {
        sg_redirect('/nachricht-gesendet/');
    }
    // Versand fehlgeschlagen: zurück zum Formular
    sg_redirect($backPath . '?fehler=1');
}

function sg_guard(string $backPath): array
{
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        sg_redirect($backPath);
    }
    // Honeypot: Menschen sehen dieses Feld nicht
    if (!empty($_POST['website'])) {
        sg_redirect('/nachricht-gesendet/'); // Bots freundlich verabschieden
    }

    $name  = sg_clean((string)($_POST['name'] ?? ''), 120);
    $email = sg_clean((string)($_POST['email'] ?? ''), 200);

    if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
        sg_redirect($backPath . '?fehler=1');
    }
    return [$name, $email];
}
