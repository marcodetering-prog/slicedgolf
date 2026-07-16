<?php
/** Sliced Golf — Werk-Anfrage (Einzelwerk-Seiten). */

declare(strict_types=1);
require __DIR__ . '/_mail.php';

$back = '/';
[$name, $email] = sg_guard($back);

$werk      = sg_clean((string)($_POST['werk'] ?? ''), 200);
$nachricht = trim(mb_substr((string)($_POST['nachricht'] ?? ''), 0, 4000));

$subject = 'Werkanfrage: ' . ($werk !== '' ? $werk : 'ohne Angabe');
$body = "Werkanfrage über slicedgolf.ch\n"
      . "──────────────────────────────\n"
      . "Werk:    {$werk}\n"
      . "Name:    {$name}\n"
      . "E-Mail:  {$email}\n"
      . "──────────────────────────────\n\n"
      . ($nachricht !== '' ? $nachricht : '(keine Nachricht)') . "\n";

sg_handle($subject, $body, $email, $back);
