import React, { type ReactNode } from 'react';
import { translate } from '@docusaurus/Translate';
import { PageMetadata } from '@docusaurus/theme-common';
import Layout from '@theme/Layout';
import Head from '@docusaurus/Head';
import NotFoundContent from '@theme/NotFound/Content';

export default function Index(): ReactNode {
  const title = translate({
    id: 'theme.NotFound.title',
    message: 'Page Not Found',
  });
  return (
    <>
      <Head>
        <meta name="robots" content="noindex, follow" />
      </Head>
      <PageMetadata title={title} />
      <Layout>
        <NotFoundContent />
      </Layout>
    </>
  );
}
