<?php
/** Sliced Golf — Kontaktformular. */

declare(strict_types=1);
require __DIR__ . '/_mail.php';

$back = '/';
[$name, $email] = sg_guard($back);

$betreffMap = [
    'werk'      => 'Werk anfragen',
    'lesson'    => 'Golf Lesson',
    'presse'    => 'Presse',
    'sonstiges' => 'Sonstiges',
];
$betreffKey = (string)($_POST['betreff'] ?? 'sonstiges');
$betreff    = $betreffMap[$betreffKey] ?? 'Sonstiges';
$nachricht  = trim(mb_substr((string)($_POST['nachricht'] ?? ''), 0, 4000));

if ($nachricht === '') {
    sg_redirect($back . '?fehler=1');
}

$subject = 'Kontaktanfrage: ' . $betreff;
$body = "Kontaktanfrage über slicedgolf.ch\n"
      . "──────────────────────────────\n"
      . "Betreff: {$betreff}\n"
      . "Name:    {$name}\n"
      . "E-Mail:  {$email}\n"
      . "──────────────────────────────\n\n"
      . $nachricht . "\n";

sg_handle($subject, $body, $email, $back);
