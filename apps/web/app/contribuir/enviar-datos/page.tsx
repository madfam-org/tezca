'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Upload, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardContent, Button, Input, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@tezca/ui';
import { LanguageToggle } from '@/components/LanguageToggle';
import { API_BASE_URL } from '@/lib/config';

const dataTypeOptions = [
  { value: 'federal', es: 'Federal', en: 'Federal', nah: 'Federal' },
  { value: 'state', es: 'Estatal', en: 'State', nah: 'Altep\u0113tl' },
  { value: 'municipal', es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
  { value: 'nom', es: 'Norma Oficial Mexicana (NOM)', en: 'Official Mexican Standard (NOM)', nah: 'NOM tenahuatilli' },
  { value: 'judicial', es: 'Judicial', en: 'Judicial', nah: 'Tlaht\u014dcayōtl' },
  { value: 'treaty', es: 'Tratado internacional', en: 'International treaty', nah: 'C\u0113m\u0101n\u0101huac tlan\u014dn\u014dtzaliztli' },
  { value: 'regulation', es: 'Reglamento', en: 'Regulation', nah: 'Reglamento' },
  { value: 'other', es: 'Otro', en: 'Other', nah: 'Oc c\u0113' },
];

const fileFormatOptions = [
  { value: 'pdf', label: 'PDF' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'xml', label: 'XML' },
  { value: 'other', es: 'Otro', en: 'Other', nah: 'Oc c\u0113' },
];

const content = {
  es: {
    back: 'Volver a contribuir',
    title: 'Enviar datos',
    subtitle: 'Comparte fuentes legislativas para ampliar el acervo de Tezca',
    name: 'Nombre completo',
    namePlaceholder: 'Tu nombre',
    email: 'Correo electr\u00f3nico',
    emailPlaceholder: 'correo@ejemplo.com',
    institution: 'Instituci\u00f3n (opcional)',
    institutionPlaceholder: 'Universidad, despacho, organizaci\u00f3n...',
    dataType: 'Tipo de datos',
    dataTypePlaceholder: 'Selecciona un tipo',
    jurisdiction: 'Jurisdicci\u00f3n',
    jurisdictionPlaceholder: 'Ej: Jalisco, CDMX, Federal...',
    description: 'Descripci\u00f3n',
    descriptionPlaceholder: 'Describe los datos que tienes disponibles: qu\u00e9 contienen, periodo que cubren, fuente original...',
    fileUrl: 'URL del archivo (opcional)',
    fileUrlPlaceholder: 'https://ejemplo.com/datos.pdf',
    fileFormat: 'Formato del archivo',
    fileFormatPlaceholder: 'Selecciona un formato',
    submit: 'Enviar datos',
    submitting: 'Enviando...',
    successTitle: 'Datos enviados',
    successBody: 'Gracias por tu contribuci\u00f3n. Revisaremos la informaci\u00f3n y te contactaremos si necesitamos m\u00e1s detalles.',
    errorTitle: 'Error al enviar',
    errorBody: 'No se pudo enviar el formulario. Por favor int\u00e9ntalo de nuevo m\u00e1s tarde.',
    backToContribute: 'Volver a contribuir',
  },
  en: {
    back: 'Back to contribute',
    title: 'Submit data',
    subtitle: 'Share legislative sources to expand Tezca\'s collection',
    name: 'Full name',
    namePlaceholder: 'Your name',
    email: 'Email',
    emailPlaceholder: 'email@example.com',
    institution: 'Institution (optional)',
    institutionPlaceholder: 'University, firm, organization...',
    dataType: 'Data type',
    dataTypePlaceholder: 'Select a type',
    jurisdiction: 'Jurisdiction',
    jurisdictionPlaceholder: 'E.g.: Jalisco, CDMX, Federal...',
    description: 'Description',
    descriptionPlaceholder: 'Describe the data you have available: what it contains, the period it covers, original source...',
    fileUrl: 'File URL (optional)',
    fileUrlPlaceholder: 'https://example.com/data.pdf',
    fileFormat: 'File format',
    fileFormatPlaceholder: 'Select a format',
    submit: 'Submit data',
    submitting: 'Submitting...',
    successTitle: 'Data submitted',
    successBody: 'Thank you for your contribution. We will review the information and contact you if we need more details.',
    errorTitle: 'Submission error',
    errorBody: 'The form could not be submitted. Please try again later.',
    backToContribute: 'Back to contribute',
  },
  nah: {
    back: 'Xicmocuepa pal\u0113huiliztli',
    title: 'Xict\u012btlani tlamachiliztli',
    subtitle: 'Xicn\u0113xtia tenahuatiliz tlamachilizpial\u014dyan ic mohueyilia Tezca',
    name: 'Mot\u014dcā',
    namePlaceholder: 'Mot\u014dcā',
    email: 'Correo',
    emailPlaceholder: 'correo@ejemplo.com',
    institution: 'Tlamachtiloyan (ahmo monequi)',
    institutionPlaceholder: 'Tlamachtiloyan, tlanōnōtzaloyan...',
    dataType: 'Tlamachiliztli',
    dataTypePlaceholder: 'Xictlalia c\u0113',
    jurisdiction: 'Jurisdicci\u00f3n',
    jurisdictionPlaceholder: 'Ej: Jalisco, CDMX, Federal...',
    description: 'Tlan\u0113xtiliztli',
    descriptionPlaceholder: 'Xict\u0113n\u0113hua in tlamachiliztli: tl\u0113in quipiya, qu\u0113zqui xihuitl, c\u0101mpa hu\u0101llauh...',
    fileUrl: '\u0100matl URL (ahmo monequi)',
    fileUrlPlaceholder: 'https://ejemplo.com/datos.pdf',
    fileFormat: '\u0100matl formato',
    fileFormatPlaceholder: 'Xictlalia c\u0113',
    submit: 'Xict\u012btlani',
    submitting: 'Mot\u012btlania...',
    successTitle: 'Motītlanilōc',
    successBody: 'Tlazohcāmati ic motlapal\u0113huiliztli. Tictlachiyazqu\u0113 ihuan timitznōnōtzazqu\u0113.',
    errorTitle: 'Ahmo huelīc',
    errorBody: 'Ahmo huel\u012bc motītlani. Xicyēyeco oc c\u0113ppa.',
    backToContribute: 'Xicmocuepa pal\u0113huiliztli',
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

export default function EnviarDatosPage() {
  const [lang] = useState<Lang>(getLangFromSearch);
  const t = content[lang];

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    institution: '',
    dataType: '',
    jurisdiction: '',
    description: '',
    fileUrl: '',
    fileFormat: '',
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');

  function handleChange(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('submitting');

    try {
      const res = await fetch(`${API_BASE_URL}/contributions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          institution: formData.institution || undefined,
          data_type: formData.dataType,
          jurisdiction: formData.jurisdiction,
          description: formData.description,
          file_url: formData.fileUrl || undefined,
          file_format: formData.fileFormat,
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
          <Upload className="h-10 w-10 text-primary-200 mx-auto mb-4" aria-hidden="true" />
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

          {/* Data type */}
          <div className="space-y-2">
            <Label>{t.dataType} *</Label>
            <Select
              required
              value={formData.dataType}
              onValueChange={(value: string) => handleChange('dataType', value)}
            >
              <SelectTrigger className="w-full" aria-label={t.dataType}>
                <SelectValue placeholder={t.dataTypePlaceholder} />
              </SelectTrigger>
              <SelectContent>
                {dataTypeOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt[lang]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Jurisdiction */}
          <div className="space-y-2">
            <Label htmlFor="jurisdiction">{t.jurisdiction} *</Label>
            <Input
              id="jurisdiction"
              type="text"
              required
              placeholder={t.jurisdictionPlaceholder}
              value={formData.jurisdiction}
              onChange={(e) => handleChange('jurisdiction', e.target.value)}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">{t.description} *</Label>
            <textarea
              id="description"
              required
              rows={5}
              placeholder={t.descriptionPlaceholder}
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 dark:bg-input/30 w-full rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
            />
          </div>

          {/* File URL */}
          <div className="space-y-2">
            <Label htmlFor="fileUrl">{t.fileUrl}</Label>
            <Input
              id="fileUrl"
              type="url"
              placeholder={t.fileUrlPlaceholder}
              value={formData.fileUrl}
              onChange={(e) => handleChange('fileUrl', e.target.value)}
            />
          </div>

          {/* File format */}
          <div className="space-y-2">
            <Label>{t.fileFormat} *</Label>
            <Select
              required
              value={formData.fileFormat}
              onValueChange={(value: string) => handleChange('fileFormat', value)}
            >
              <SelectTrigger className="w-full" aria-label={t.fileFormat}>
                <SelectValue placeholder={t.fileFormatPlaceholder} />
              </SelectTrigger>
              <SelectContent>
                {fileFormatOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {'label' in opt ? opt.label : opt[lang]}
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
