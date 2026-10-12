'use client';

import { useEffect, useState } from 'react';
import { EcosystemBanner, type EcosystemPlatform } from '@madfam/ecosystem-banner';

import { ECOSYSTEM_BANNER_PLATFORMS, tagEcosystemPlatforms } from '@/lib/ecosystem-banner-platforms';

export function EcosystemBannerClient() {
  const [platforms, setPlatforms] =
    useState<readonly EcosystemPlatform[]>(ECOSYSTEM_BANNER_PLATFORMS);

  // UTM tags need the page host, so they are applied after mount; the server
  // render (and the banner, which renders nothing before mount) is unchanged.
  useEffect(() => {
    setPlatforms(tagEcosystemPlatforms(ECOSYSTEM_BANNER_PLATFORMS, window.location.hostname));
  }, []);

  return <EcosystemBanner testId="ecosystem-banner" platforms={platforms} />;
}
