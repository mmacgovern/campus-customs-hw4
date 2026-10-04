// The Campus Customs shield mark, drawn inline so it stays crisp at any size.
export default function Crest({ size = 36 }: { size?: number }) {
  return (
    <svg
      className="crest"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M32 3 56 11v20c0 15-10.5 25-24 30C18.5 56 8 46 8 31V11z"
        fill="currentColor"
        stroke="#fff"
        strokeWidth="3"
      />
      <path d="M14 17h36" stroke="#fff" strokeWidth="1.5" opacity="0.5" />
      <text
        x="32"
        y="42"
        textAnchor="middle"
        fontFamily="'Playfair Display', Georgia, serif"
        fontWeight="800"
        fontSize="21"
        fill="#fff"
      >
        CC
      </text>
    </svg>
  )
}
