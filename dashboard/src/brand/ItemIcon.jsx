// Simple line icons for the checked items (stroke follows currentColor).
const paths = {
  mask: (
    <>
      <path d="M4 9.5c2.5-1.2 5.2-1.8 8-1.8s5.5.6 8 1.8v3.2c0 3.6-3.6 6.3-8 6.3s-8-2.7-8-6.3z" />
      <path d="M4 10.5H2.5M20 10.5h1.5M8 12h8M8.5 15h7" />
    </>
  ),
  gloves: (
    <>
      <path d="M7 21v-3.5L4.6 12.8a1.4 1.4 0 0 1 2.3-1.6L8.5 13V5.5a1.25 1.25 0 0 1 2.5 0V11V4a1.25 1.25 0 0 1 2.5 0v7V5a1.25 1.25 0 0 1 2.5 0v6.5V7.5a1.25 1.25 0 0 1 2.5 0v7.2c0 2.6-1.4 4.3-3 5.3v1" />
      <path d="M7 18.5h10" />
    </>
  ),
};

export default function ItemIcon({ item, size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[item]}
    </svg>
  );
}
