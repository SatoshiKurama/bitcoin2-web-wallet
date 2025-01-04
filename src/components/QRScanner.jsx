import React, { useEffect } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';

function QRScanner({ onScan }) {
  useEffect(() => {
    const scanner = new Html5QrcodeScanner('reader', {
      fps: 5,
      qrbox: { width: 250, height: 250 }
    });

    scanner.render(
      (decodedText) => {
        onScan(decodedText);
        scanner.clear();
      },
      (err) => {
        console.warn('QR Code scan error:', err);
      }
    );

    return () => {
      scanner.clear().catch((error) => {
        console.error('Failed to clear scanner', error);
      });
    };
  }, [onScan]);

  return (
    <div style={{ textAlign: 'center', marginTop: '20px' }}>
      <div id="reader"></div>
    </div>
  );
}

export default QRScanner;