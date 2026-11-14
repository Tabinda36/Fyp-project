// Helpers shared by the admin course-management pages (CoursesInfo, AddCourse, CourseDetails, Level*).

/**
 * React's `style` prop cannot express `!important`. The templates used inline
 * `style="color: #047857 !important;"` to beat Bootstrap utilities (.text-muted, .border-top ...),
 * so apply those declarations through a ref:  <p ref={important({ color: '#047857' })}>
 */
export function important(decls) {
  return (el) => {
    if (!el) return;
    Object.entries(decls).forEach(([prop, value]) => el.style.setProperty(prop, value, 'important'));
  };
}
