'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Users, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardContent, Button, Input, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import { API_BASE_URL } from '@/lib/config';

const expertiseOptions = [
  { value: 'constitucional', es: 'Derecho constitucional', en: 'Constitutional law', nah: 'Constitucional tenahuatilli' },
  { value: 'fiscal', es: 'Derecho fiscal', en: 'Tax law', nah: 'Fiscal tenahuatilli' },
  { value: 'laboral', es: 'Derecho laboral', en: 'Labor law', nah: 'Tequitl tenahuatilli' },
  { value: 'administrativo', es: 'Derecho administrativo', en: 'Administrative law', nah: 'Tl\u0101t\u014dcayōtl tenahuatilli' },
  { value: 'penal', es: 'Derecho penal', en: 'Criminal law', nah: 'Tlahtlacōlli tenahuatilli' },
  { value: 'ambiental', es: 'Derecho ambiental', en: 'Environmental law', nah: 'Tlālticpac tenahuatilli' },
  { value: 'comercial', es: 'Derecho comercial', en: 'Commercial law', nah: 'Tlanāmacaliztli tenahuatilli' },
  { value: 'internacional', es: 'Derecho internacional', en: 'International law', nah: 'C\u0113m\u0101n\u0101huac tenahuatilli' },
];

const contactPreferenceOptions = [
  { value: 'email', es: 'Correo electr\u00f3nico', en: 'Email', nah: 'Correo' },
  { value: 'phone', es: 'Tel\u00e9fono', en: 'Phone', nah: 'Tel\u00e9fono' },
];

const content = {
  es: {
    back: 'Volver a contribuir',
    title: 'Contacto de experto',
    subtitle: 'Comparte tu experiencia para fortalecer el acervo legislativo de M\u00e9xico',
    name: 'Nombre completo',
    namePlaceholder: 'Tu nombre',
    email: 'Correo electr\u00f3nico',
    emailPlaceholder: 'correo@ejemplo.com',
    institution: 'Instituci\u00f3n (opcional)',
    institutionPlaceholder: 'Universidad, despacho, organizaci\u00f3n...',
    expertise: '\u00c1rea de especialidad',
    expertisePlaceholder: 'Selecciona un \u00e1rea',
    help: '\u00bfC\u00f3mo puedes ayudar?',
    helpPlaceholder: 'Describe tu experiencia y c\u00f3mo podr\u00edas contribuir a Tezca. Por ejemplo: verificaci\u00f3n de textos, clasificaci\u00f3n de leyes, asesor\u00eda sobre fuentes...',
    contactPreference: 'Preferencia de contacto',
    contactPlaceholder: 'Selecciona una opci\u00f3n',
    submit: 'Enviar',
    submitting: 'Enviando...',
    successTitle: 'Mensaje enviado',
    successBody: 'Gracias por tu inter\u00e9s en contribuir. Nos pondremos en contacto contigo pronto.',
    errorTitle: 'Error al enviar',
    errorBody: 'No se pudo enviar el formulario. Por favor int\u00e9ntalo de nuevo m\u00e1s tarde.',
    backToContribute: 'Volver a contribuir',
    required: 'Este campo es obligatorio',
  },
  en: {
    back: 'Back to contribute',
    title: 'Expert contact',
    subtitle: 'Share your expertise to strengthen Mexico\'s legislative collection',
    name: 'Full name',
    namePlaceholder: 'Your name',
    email: 'Email',
    emailPlaceholder: 'email@example.com',
    institution: 'Institution (optional)',
    institutionPlaceholder: 'University, firm, organization...',
    expertise: 'Area of expertise',
    expertisePlaceholder: 'Select an area',
    help: 'How can you help?',
    helpPlaceholder: 'Describe your experience and how you could contribute to Tezca. For example: text verification, law classification, source advisory...',
    contactPreference: 'Contact preference',
    contactPlaceholder: 'Select an option',
    submit: 'Submit',
    submitting: 'Submitting...',
    successTitle: 'Message sent',
    successBody: 'Thank you for your interest in contributing. We will contact you soon.',
    errorTitle: 'Submission error',
    errorBody: 'The form could not be submitted. Please try again later.',
    backToContribute: 'Back to contribute',
    required: 'This field is required',
  },
  nah: {
    back: 'Xicmocuepa pal\u0113huiliztli',
    title: 'Tlamatini t\u0113n\u014dn\u014dtzaliztli',
    subtitle: 'Xicn\u0113xtia motlamatiliztli ic motl\u0101lia in m\u0113xihcatl tenahuatilli',
    name: 'Mot\u014dcā',
    namePlaceholder: 'Mot\u014dcā',
    email: 'Correo',
    emailPlaceholder: 'correo@ejemplo.com',
    institution: 'Tlamachtiloyan (ahmo monequi)',
    institutionPlaceholder: 'Tlamachtiloyan, tlanōnōtzaloyan...',
    expertise: 'Motlamatiliztli',
    expertisePlaceholder: 'Xictlalia c\u0113',
    help: '\u00bfQu\u0113nin ticpal\u0113huiz?',
    helpPlaceholder: 'Xict\u0113n\u0113hua motlamatiliztli ihuan qu\u0113nin ticpal\u0113huiz Tezca...',
    contactPreference: 'T\u0113n\u014dn\u014dtzaliztli',
    contactPlaceholder: 'Xictlalia c\u0113',
    submit: 'Xict\u012btlani',
    submitting: 'Mot\u012btlania...',
    successTitle: 'Motītlanilōc',
    successBody: 'Tlazohcāmati ic motlapal\u0113huiliztli. Timitznōnōtzazqu\u0113 nimān.',
    errorTitle: 'Ahmo huelīc',
    errorBody: 'Ahmo huel\u012bc motītlani. Xicyēyeco oc c\u0113ppa.',
    backToContribute: 'Xicmocuepa pal\u0113huiliztli',
    required: 'In\u012bn monequi',
  },
};

type Lang = 'es' | 'en' | 'nah';

function getLangFromSearch(): Lang {
  if (typeof window === 'undefined') return 'es';
  const params = new URLSearchParams(window.location.search);
  const lang = params.get('lang');
  if (lang === 'en' || lang === 'nah') return lang;
  return 'es';
}

export default function ContactoPage() {
  const [lang] = useState<Lang>(getLangFromSearch);
  const t = content[lang];

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    institution: '',
    expertise: '',
    help: '',
    contactPreference: '',
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');

  function handleChange(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('submitting');

    try {
      const res = await fetch(`${API_BASE_URL}/contributions/expert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          institution: formData.institution || undefined,
          expertise_area: formData.expertise,
          description: formData.help,
          contact_preference: formData.contactPreference,
        }),
      });

      if (res.ok) {
        setStatus('success');
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    }
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 sm:px-6 py-16 max-w-2xl">
          <Card>
            <CardContent className="p-8 text-center space-y-4">
              <CheckCircle2 className="h-12 w-12 text-primary mx-auto" aria-hidden="true" />
              <h1 className="font-serif text-2xl font-semibold text-foreground">{t.successTitle}</h1>
              <p className="text-muted-foreground">{t.successBody}</p>
              <Link
                href="/contribuir"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-medium mt-4"
              >
                <ArrowLeft className="h-4 w-4" />
                {t.backToContribute}
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-900 via-primary-800 to-secondary-900 px-4 sm:px-6 py-16 sm:py-20">
        <div className="absolute inset-0 bg-grid-pattern opacity-10" />
        <div className="relative mx-auto max-w-2xl text-center">
          <Users className="h-10 w-10 text-primary-200 mx-auto mb-4" aria-hidden="true" />
          <h1 className="font-display text-3xl sm:text-5xl font-bold tracking-tight text-white">
            {t.title}
          </h1>
          <p className="mt-3 sm:mt-4 font-serif text-lg sm:text-xl text-primary-200 italic">
            {t.subtitle}
          </p>
        </div>
      </section>

      {/* Navigation bar */}
      <div className="container mx-auto px-4 sm:px-6 py-6 max-w-2xl">
        <div className="flex items-center justify-between">
          <Link
            href="/contribuir"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.back}
          </Link>
          <LanguageToggle />
        </div>
      </div>

      {/* Form */}
      <div className="container mx-auto px-4 sm:px-6 pb-16 sm:pb-24 max-w-2xl">
        {status === 'error' && (
          <div className="mb-6 flex items-start gap-3 rounded-md bg-destructive/10 p-4">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-medium text-destructive">{t.errorTitle}</p>
              <p className="text-sm text-destructive/80">{t.errorBody}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">{t.name} *</Label>
            <Input
              id="name"
              type="text"
              required
              placeholder={t.namePlaceholder}
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="email">{t.email} *</Label>
            <Input
              id="email"
              type="email"
              required
              placeholder={t.emailPlaceholder}
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
            />
          </div>

          {/* Institution */}
          <div className="space-y-2">
            <Label htmlFor="institution">{t.institution}</Label>
            <Input
              id="institution"
              type="text"
              placeholder={t.institutionPlaceholder}
              value={formData.institution}
              onChange={(e) => handleChange('institution', e.target.value)}
            />
          </div>

          {/* Expertise area */}
          <div className="space-y-2">
            <Label>{t.expertise} *</Label>
            <Select
              required
              value={formData.expertise}
              onValueChange={(value: string) => handleChange('expertise', value)}
            >
              <SelectTrigger className="w-full" aria-label={t.expertise}>
                <SelectValue placeholder={t.expertisePlaceholder} />
              </SelectTrigger>
              <SelectContent>
                {expertiseOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt[lang]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* How can you help */}
          <div className="space-y-2">
            <Label htmlFor="help">{t.help} *</Label>
            <textarea
              id="help"
              required
              rows={5}
              placeholder={t.helpPlaceholder}
              value={formData.help}
              onChange={(e) => handleChange('help', e.target.value)}
              className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 dark:bg-input/30 w-full rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
            />
          </div>

          {/* Contact preference */}
          <div className="space-y-2">
            <Label>{t.contactPreference} *</Label>
            <Select
              required
              value={formData.contactPreference}
              onValueChange={(value: string) => handleChange('contactPreference', value)}
            >
              <SelectTrigger className="w-full" aria-label={t.contactPreference}>
                <SelectValue placeholder={t.contactPlaceholder} />
              </SelectTrigger>
              <SelectContent>
                {contactPreferenceOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt[lang]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            size="lg"
            disabled={status === 'submitting'}
            className="w-full sm:w-auto"
          >
            {status === 'submitting' ? t.submitting : t.submit}
          </Button>
        </form>
      </div>
    </div>
  );
}
