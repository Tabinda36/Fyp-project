// Port of student_dashboard/certificate_verify.html (public, standalone).
import { Link, useParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { BOOTSTRAP_530, ICONS_1111, googleFont } from '../../cdn';
import { djDate } from '../../utils/djangoFormat';
import rawCss from './CertificateVerifyPage.css?raw';
import { ROOT_PASSTHROUGH } from './rootPassthrough';

const css = rawCss + ROOT_PASSTHROUGH;

const FONTS = googleFont('family=Cinzel:wght@700;900&family=Poppins:wght@400;600;700;800&family=Montserrat:wght@500;700');

export default function CertificateVerifyPage() {
  const { certId } = useParams();
  usePageAssets({ links: [BOOTSTRAP_530, ICONS_1111, FONTS], css, title: `ALVIX Credential Verification | ${certId}` });
  const { data, ready } = usePageData(`/public/certificates/${encodeURIComponent(certId)}/verify/`);

  if (!ready) return null;
  const certificate = data.certificate;

  return (
    <div className="verify-card">
      {/* Header */}
      <div className="verify-header">
        <div className="verify-logo-text">★ ALVIX ACADEMY ★</div>
        <div className="gold-pill">Official Public Verification Registry</div>
      </div>

      {/* Body */}
      <div className="verify-body">
        {data.is_valid ? (
          <>
            {/* VALID STATUS */}
            <div className="status-badge-valid">
              <i className="bi bi-patch-check-fill fs-1 text-success d-block mb-1"></i>
              <h4 className="fw-bold mb-1">OFFICIALLY VERIFIED &amp; VALID</h4>
              <p className="small mb-0">This credential is authenticated by the ALVIX Academic Integrity Protocol.</p>
            </div>

            {/* Meta details */}
            <div className="meta-row">
              <span className="meta-label">Certificate ID:</span>
              <span className="meta-value font-monospace text-primary">{certificate.certificate_id}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Student Recipient:</span>
              <span className="meta-value">{certificate.student_name}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Student Email:</span>
              <span className="meta-value text-muted">{certificate.student_email}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Masterclass Track:</span>
              <span className="meta-value">{certificate.course_name}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Benchmark Level:</span>
              <span className="meta-value">{certificate.level}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Overall Percentage:</span>
              <span className="meta-value text-success fs-6">{certificate.overall_percentage}% (Grade {certificate.performance_grade})</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Active Learning Duration:</span>
              <span className="meta-value">{djDate(certificate.start_date, 'M d, Y')} &ndash; {djDate(certificate.current_date, 'M d, Y')} ({certificate.duration_days} days)</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Verification Time:</span>
              <span className="meta-value text-muted small">{djDate(data.verification_time, 'Y-m-d H:i:s')} UTC</span>
            </div>

            {/* AI Review Summary */}
            {certificate.ai_review ? (
              <div className="ai-review-box">
                <strong className="d-block text-dark mb-1"><i className="bi bi-cpu text-warning me-1"></i> Continuous AI Performance Review:</strong>
                {certificate.ai_review}
              </div>
            ) : null}
          </>
        ) : (
          <>
            {/* INVALID STATUS */}
            <div className="status-badge-invalid">
              <i className="bi bi-x-octagon-fill fs-1 text-danger d-block mb-1"></i>
              <h4 className="fw-bold mb-1">INVALID OR UNVERIFIED CREDENTIAL</h4>
              <p className="small mb-0">
                The requested Certificate ID <strong className="font-monospace">&quot;{data.cert_id}&quot;</strong> was not found in the verified registry or has not satisfied the graduation pass mark requirement.
              </p>
            </div>
            <p className="text-muted small text-center">
              If you believe this is an error, please ensure the student has completed the full curriculum and achieved the minimum passing grade.
            </p>
          </>
        )}

        <div className="mt-4 text-center">
          <Link to="/" className="btn btn-outline-dark btn-sm rounded-pill px-4">
            <i className="bi bi-arrow-left me-1"></i> Back to ALVIX Home
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="verify-footer">
        Accredited Worldwide &bull; Cryptographic Hash Verification &bull; &copy; 2026 ALVIX Academy
      </div>
    </div>
  );
}
