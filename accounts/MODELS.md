# Account models and role themes

This document explains the classes and behavior in [`models.py`](./models.py).

## `Role`

`Role` is a `models.TextChoices` enum used by `User.role`. Its stored values are:

| Python member | Stored value | Display label |
| --- | --- | --- |
| `Role.ADMIN` | `admin` | Administrator |
| `Role.DENTIST` | `dentist` | Dentist |
| `Role.RECEPTIONIST` | `receptionist` | Receptionist |
| `Role.PATIENT` | `patient` | Patient |

Django stores the short value in the database and uses the display label in forms and templates, for example through `user.get_role_display()`.

## `Gender`

`Gender` is a `models.TextChoices` enum for the optional gender field:

| Python member | Stored value | Display label |
| --- | --- | --- |
| `Gender.MALE` | `male` | Male |
| `Gender.FEMALE` | `female` | Female |
| `Gender.OTHER` | `other` | Other |

The field is optional; the model does not require a value.

## `ROLE_THEMES`

`ROLE_THEMES` maps each role to presentation metadata:

| Role | CSS class (`name`) | Label | Icon |
| --- | --- | --- | --- |
| Administrator | `theme-admin` | Admin Console | `bi-shield-lock` |
| Dentist | `theme-dentist` | Dentist Workspace | `bi-heart-pulse` |
| Receptionist | `theme-receptionist` | Front Desk | `bi-calendar2-week` |
| Patient | `theme-patient` | My Health | `bi-emoji-smile` |

Each entry also provides `primary`, `accent`, and `gradient` color values. The `User.theme` property returns the entry for that user's role.

### How the CSS class is used

The `theme_context` context processor makes the active theme available to templates as `active_theme`. [`base.html`](../templates/base.html) adds `active_theme.name` to the root `<html>` element. As a result, a signed-in administrator gets `<html class="theme-admin">`, for example. Signed-out pages use `theme-public`.

[`app.css`](../static/css/app.css) defines selectors for these theme classes. At present, those selectors all assign the same blue CSS variables (`--primary`, `--accent`, and `--gradient`). Therefore, although `ROLE_THEMES` has different role color values, the current stylesheet does not apply those values as role-specific CSS colors.

## `User`

`User` extends Django's `AbstractUser`, keeping Django's standard account, password, permission, and staff fields while adding clinic profile and role information. `Role` controls the application's role-specific behavior; Django's `is_staff` and `is_superuser` remain separate permission flags.

### Model fields

| Field | Type | Meaning and behavior |
| --- | --- | --- |
| `role` | `CharField`, max 20 | User role, limited to `Role` choices. Defaults to `patient`. |
| `phone` | `CharField`, max 20 | Contact phone number. Defaults to `0000000000`; blank input is allowed. |
| `gender` | `CharField`, max 10 | Optional value from `Gender`. |
| `date_of_birth` | `DateField` | Optional date. `null=True` allows a database `NULL`; `blank=True` allows an empty form value. |
| `address` | `CharField`, max 255 | Optional address. |
| `avatar` | `ImageField` | Optional image uploaded under `MEDIA_ROOT/avatars/`. |
| `bio` | `TextField` | Optional free-form profile text. |

Inherited `AbstractUser` fields include `username`, `first_name`, `last_name`, `email`, `password`, `is_staff`, `is_superuser`, and `is_active`, among others. This model does not override those inherited fields.

### Properties and methods

| Member | Kind | Behavior |
| --- | --- | --- |
| `theme` | Property | Returns the role's theme metadata. Falls back to the patient theme if the role has no matching entry. |
| `initials` | Property | Uses the first character of `first_name` (or `username` if no first name) and the first character of `last_name` when present; returns uppercase text. |
| `display_name` | Property | Returns Django's full name when available, otherwise the username. |
| `is_admin()` | Method | Returns `True` for the admin role or a Django superuser. |
| `is_dentist()` | Method | Returns `True` when the role is dentist. |
| `is_receptionist()` | Method | Returns `True` when the role is receptionist. |
| `is_patient()` | Method | Returns `True` when the role is patient. |
| `__str__()` | Method | Returns a readable string in the format `Display Name (Role Label)`. |

### Example

```python
user.display_name       # "Avery Smith", or the username if no full name is set
user.initials           # "AS"
user.get_role_display() # "Dentist"
user.theme["name"]      # "theme-dentist"
user.is_dentist()       # True for dentist accounts
```
