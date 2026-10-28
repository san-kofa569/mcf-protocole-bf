/* Cale LD_PRELOAD pour Wine : un pty n'a pas de lignes modem.
 *
 * Wine abandonne WaitCommEvent dès que TIOCMGET échoue (async_wait_proc :
 * « get_modem_status failed »), si bien qu'un programme Qt ne voit jamais
 * arriver les octets envoyés par le faux MCF. Quand un terminal répond ENOTTY
 * aux ioctl des lignes modem, la cale répond à sa place : CTS, DSR et CD levés,
 * DTR et RTS réglables. Tout autre appel, et tout vrai port série, passe tel quel.
 *
 * Sans en-têtes système, pour se compiler en 32 bits sans multilib :
 * voir simulateur/cale.py.
 */
#include <stdarg.h>

#define RTLD_NEXT ((void *) -1l)
#define ENOTTY    25
#define TCGETS    0x5401
#define TIOCMGET  0x5415
#define TIOCMBIS  0x5416
#define TIOCMBIC  0x5417
#define TIOCMSET  0x5418
#define TIOCM_DTR 0x002
#define TIOCM_RTS 0x004
#define TIOCM_CTS 0x020
#define TIOCM_CAR 0x040
#define TIOCM_DSR 0x100
#define REGLABLES (TIOCM_DTR | TIOCM_RTS)
#define LEVEES    (TIOCM_CTS | TIOCM_CAR | TIOCM_DSR)

void *dlsym(void *, const char *);
int *__errno_location(void);

static int lignes = REGLABLES | LEVEES;

typedef int (*ioctl_t)(int, unsigned long, void *);

static int caler(ioctl_t vrai, int fd, unsigned long req, void *arg)
{
    long termios[16];
    int r = vrai(fd, req, arg), e = *__errno_location();

    if (r == 0 || e != ENOTTY || (req != TIOCMGET && req != TIOCMSET && req != TIOCMBIS && req != TIOCMBIC))
        return r;
    if (vrai(fd, TCGETS, termios) != 0) {   /* pas un terminal : l'échec est légitime */
        *__errno_location() = e;
        return r;
    }
    if (req == TIOCMGET)
        *(int *) arg = lignes;
    else if (req == TIOCMSET)
        lignes = (*(int *) arg & REGLABLES) | LEVEES;
    else if (req == TIOCMBIS)
        lignes |= *(int *) arg & REGLABLES;
    else
        lignes &= ~(*(int *) arg & REGLABLES);
    return 0;
}

#define POINT_D_ENTREE(nom)                                         \
int nom(int fd, unsigned long req, ...)                             \
{                                                                   \
    static ioctl_t vrai;                                            \
    va_list ap;                                                     \
    void *arg;                                                      \
                                                                    \
    va_start(ap, req);                                              \
    arg = va_arg(ap, void *);                                       \
    va_end(ap);                                                     \
    if (!vrai)                                                      \
        vrai = (ioctl_t) dlsym(RTLD_NEXT, #nom);                    \
    return caler(vrai, fd, req, arg);                               \
}

POINT_D_ENTREE(ioctl)
#ifdef __i386__
/* Wine i386 est compilé avec time_t 64 bits : ntdll.so importe ce symbole-là. */
POINT_D_ENTREE(__ioctl_time64)
#endif
