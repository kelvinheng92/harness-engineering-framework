export interface HighlightColor {
  bg: string      // rgba background for the overlay
  border: string  // solid border color
  swatch: string  // Tailwind bg class for the card swatch dot
}

// Distinct palette — chosen to be visually separable and accessible
export const HIGHLIGHT_COLORS: HighlightColor[] = [
  { bg: 'rgba(200,16,46,0.18)',   border: '#C8102E', swatch: 'bg-[#C8102E]' },   // OCBC red
  { bg: 'rgba(124,58,237,0.18)',  border: '#7C3AED', swatch: 'bg-[#7C3AED]' },   // violet
  { bg: 'rgba(37,99,235,0.18)',   border: '#2563EB', swatch: 'bg-[#2563EB]' },   // blue
  { bg: 'rgba(13,148,136,0.18)', border: '#0D9488', swatch: 'bg-[#0D9488]' },   // teal
  { bg: 'rgba(217,119,6,0.18)',  border: '#D97706', swatch: 'bg-[#D97706]' },   // amber
  { bg: 'rgba(219,39,119,0.18)', border: '#DB2777', swatch: 'bg-[#DB2777]' },   // pink
  { bg: 'rgba(5,150,105,0.18)',  border: '#059669', swatch: 'bg-[#059669]' },   // emerald
  { bg: 'rgba(67,56,202,0.18)',  border: '#4338CA', swatch: 'bg-[#4338CA]' },   // indigo
  { bg: 'rgba(234,88,12,0.18)',  border: '#EA580C', swatch: 'bg-[#EA580C]' },   // orange
  { bg: 'rgba(15,118,110,0.18)', border: '#0F766E', swatch: 'bg-[#0F766E]' },   // dark teal
]

export function getColor(index: number): HighlightColor {
  return HIGHLIGHT_COLORS[index % HIGHLIGHT_COLORS.length]
}
