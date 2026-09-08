import React, { type ReactNode } from 'react';
import { useLocation } from '@docusaurus/router';
import OriginalNavbar from '@theme-original/Navbar';
import Header from '../../components/Landing/Header';

export default function Navbar(): ReactNode {
  const { pathname } = useLocation();
  const isDocumentation = pathname === '/docs' || pathname.startsWith('/docs/');
  return isDocumentation ? <OriginalNavbar /> : <Header />;
}
