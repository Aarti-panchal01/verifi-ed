/**
 * ScoreCircle — Animated radial score display
 */
export default function ScoreCircle({ score, size = 120, label = 'Score' }) {
    const radius = (size - 12) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    const tierColor = score >= 90 ? 'var(--tier-exceptional)'
        : score >= 70 ? 'var(--tier-strong)'
            : score >= 50 ? 'var(--tier-moderate)'
                : score >= 30 ? 'var(--tier-developing)'
                    : 'var(--tier-minimal)';

    const tierLabel = score >= 90 ? 'Exceptional'
        : score >= 70 ? 'Strong'
            : score >= 50 ? 'Moderate'
                : score >= 30 ? 'Developing'
                    : 'Minimal';

    return (
        <div className="score-circle" style={{ width: size, height: size }}>
            <svg className="score-svg" width={size} height={size}>
                <circle
                    className="score-circle-bg"
                    stroke="var(--border-subtle)"
                    strokeWidth="4"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
                <circle
                    className="score-circle-fill"
                    stroke={tierColor}
                    strokeWidth="4"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                    style={{
                        strokeDasharray: `${circumference} ${circumference}`,
                        strokeDashoffset: offset
                    }}
                />
            </svg>
            <div className="score-circle-value">
                <span className="score-number" style={{ color: tierColor }}>{score}</span>
                <span className="score-label">{label}</span>
            </div>
        </div>
    );
}
