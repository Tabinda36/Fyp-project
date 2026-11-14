import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import ConfirmDialog from './ConfirmDialog';
import { apiMessage, avatarHue, deleteUser, errorText, initials, normalizeUser } from './userUtils';
import css from './UserManagementPage.css?raw';
import AdminLoader from '../../layouts/AdminLoader';

/* User Management: searchable, filterable list. Editing happens on /user_management/:id/. */

const TABS = [
  { key: 'all', label: 'All users', test: () => true },
  { key: 'active', label: 'Active', test: (u) => u.is_active },
  { key: 'inactive', label: 'Inactive', test: (u) => !u.is_active },
  { key: 'enrolled', label: 'Enrolled', test: (u) => u.courses.length > 0 },
  { key: 'none', label: 'No courses', test: (u) => u.courses.length === 0 },
];

export function UserAvatar({ name, size = 'md' }) {
  return (
    <span className={`um-avatar um-avatar--${size}`} style={{ '--hue': avatarHue(name) }} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

function StatusBadge({ active }) {
  return (
    <span className={`um-status ${active ? 'is-active' : 'is-inactive'}`}>
      <span className="um-status__dot" />
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

function CourseChips({ courses, max = 2 }) {
  if (!courses.length) return <span className="um-empty-text">No course enrolled</span>;
  const shown = courses.slice(0, max);
  return (
    <div className="um-chips">
      {shown.map((c, i) => <span key={i} className="um-chip" title={c}>{c}</span>)}
      {courses.length > max ? <span className="um-chip um-chip--more" title={courses.slice(max).join(', ')}>+{courses.length - max}</span> : null}
    </div>
  );
}

export default function UserManagementPage() {
  usePageAssets({ css });
  const { data, ready, reload } = usePageData('/admin/users/');
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState('all');
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const users = useMemo(() => (ready ? (data.users || []).map(normalizeUser) : []), [ready, data]);

  const counts = useMemo(
    () => Object.fromEntries(TABS.map((t) => [t.key, users.filter(t.test).length])),
    [users],
  );

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const tabTest = TABS.find((t) => t.key === tab).test;
    return users.filter((u) => tabTest(u) && (!term || [u.username, u.email, u.phone, u.dob, ...u.courses]
      .join(' ').toLowerCase().includes(term)));
  }, [users, query, tab]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    const loading = toast.loading(`Deleting ${pendingDelete.username}…`);
    try {
      const res = await deleteUser(pendingDelete.id);
      toast.success(apiMessage(res, `User ${pendingDelete.username} deleted.`), { id: loading });
    } catch (err) {
      toast.error(errorText(err, 'Could not delete this user.'), { id: loading });
    } finally {
      setDeleting(false);
      setPendingDelete(null);
      reload();
    }
  }

  if (!ready) return <AdminLoader label="Loading users" />;

  return (
    <div className="um-page">
      {/* Header */}
      <header className="um-head">
        <div>
          <h2 className="um-head__title">Users</h2>
          <p className="um-head__sub">View, search and manage every student account.</p>
        </div>
        <label className="um-search">
          <i className="bi bi-search" aria-hidden="true"></i>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, email, phone, course…"
            aria-label="Search users"
          />
          {query ? (
            <button type="button" className="um-search__clear" onClick={() => setQuery('')} aria-label="Clear search">
              <i className="bi bi-x-circle-fill"></i>
            </button>
          ) : null}
        </label>
      </header>

      {/* Summary */}
      <section className="um-summary" aria-label="User summary">
        {[
          { label: 'Total users', value: counts.all, icon: 'bi-people-fill', tone: 'emerald' },
          { label: 'Active', value: counts.active, icon: 'bi-person-check-fill', tone: 'teal' },
          { label: 'Inactive', value: counts.inactive, icon: 'bi-person-x-fill', tone: 'rose' },
          { label: 'Enrolled in a course', value: counts.enrolled, icon: 'bi-journal-check', tone: 'gold' },
        ].map((s) => (
          <div key={s.label} className={`um-sum um-sum--${s.tone}`}>
            <span className="um-sum__icon"><i className={`bi ${s.icon}`}></i></span>
            <div>
              <strong>{s.value}</strong>
              <small>{s.label}</small>
            </div>
          </div>
        ))}
      </section>

      {/* Tabs */}
      <div className="um-tabs" role="tablist" aria-label="Filter users">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`um-tab${tab === t.key ? ' is-active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
            <span className="um-tab__count">{counts[t.key]}</span>
          </button>
        ))}
      </div>

      {/* List */}
      <section className="um-card">
        {visible.length === 0 ? (
          <div className="um-empty">
            <span className="um-empty__icon"><i className="bi bi-person-slash"></i></span>
            <strong>{users.length ? 'No users match your filters' : 'No users found in the database'}</strong>
            <small>{users.length ? 'Try a different search or tab.' : 'New students appear here after they sign up.'}</small>
            {query || tab !== 'all' ? (
              <button type="button" className="um-btn um-btn--soft" onClick={() => { setQuery(''); setTab('all'); }}>
                Reset filters
              </button>
            ) : null}
          </div>
        ) : (
          <>
            {/* Desktop / tablet table */}
            <div className="um-table-wrap">
              <table className="um-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Phone</th>
                    <th>Enrolled courses</th>
                    <th>Date of birth</th>
                    <th>Status</th>
                    <th className="um-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((u) => (
                    <tr key={u.id} onClick={() => navigate(`/user_management/${u.id}/`)} className="um-row">
                      <td>
                        <div className="um-user">
                          <UserAvatar name={u.username} />
                          <div className="um-user__text">
                            <strong>{u.username}</strong>
                            <small>{u.email || '—'}</small>
                          </div>
                        </div>
                      </td>
                      <td>{u.phone || <span className="um-empty-text">Not provided</span>}</td>
                      <td><CourseChips courses={u.courses} /></td>
                      <td>{u.dob || <span className="um-empty-text">Not provided</span>}</td>
                      <td><StatusBadge active={u.is_active} /></td>
                      <td className="um-right" onClick={(e) => e.stopPropagation()}>
                        <div className="um-actions">
                          <Link to={`/user_management/${u.id}/`} className="um-icon-btn" title="View details" aria-label={`View ${u.username}`}>
                            <i className="bi bi-eye"></i>
                          </Link>
                          <Link to={`/user_management/${u.id}/?tab=edit`} className="um-icon-btn um-icon-btn--edit" title="Edit user" aria-label={`Edit ${u.username}`}>
                            <i className="bi bi-pencil-square"></i>
                          </Link>
                          <button type="button" className="um-icon-btn um-icon-btn--danger" title="Delete user" aria-label={`Delete ${u.username}`} onClick={() => setPendingDelete(u)}>
                            <i className="bi bi-trash3"></i>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <ul className="um-cards">
              {visible.map((u) => (
                <li key={u.id} className="um-mcard">
                  <Link to={`/user_management/${u.id}/`} className="um-mcard__main">
                    <UserAvatar name={u.username} />
                    <div className="um-user__text">
                      <strong>{u.username}</strong>
                      <small>{u.email || '—'}</small>
                    </div>
                    <StatusBadge active={u.is_active} />
                  </Link>
                  <div className="um-mcard__meta">
                    <span><i className="bi bi-telephone"></i> {u.phone || 'Not provided'}</span>
                    <span><i className="bi bi-journal-bookmark"></i> {u.courses.length} course{u.courses.length === 1 ? '' : 's'}</span>
                  </div>
                  <div className="um-mcard__actions">
                    <Link to={`/user_management/${u.id}/?tab=edit`} className="um-btn um-btn--soft"><i className="bi bi-pencil-square"></i> Edit</Link>
                    <button type="button" className="um-btn um-btn--danger-soft" onClick={() => setPendingDelete(u)}><i className="bi bi-trash3"></i> Delete</button>
                  </div>
                </li>
              ))}
            </ul>

            <footer className="um-card__foot">
              Showing <strong>{visible.length}</strong> of <strong>{users.length}</strong> users
            </footer>
          </>
        )}
      </section>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this user?"
        message={pendingDelete ? `${pendingDelete.username} will be permanently removed.` : ''}
        detail="Their account, enrollments and learning progress will be deleted. This cannot be undone."
        confirmLabel="Yes, delete user"
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
