# Production deployment safety checklist

- [ ] Full Python tests and Astro build passed for the exact commit.
- [ ] Secret scan passed.
- [ ] Staging deployment succeeded.
- [ ] Controlled staging verification was recorded.
- [ ] Manual approval was granted through the protected production environment.
- [ ] Current external configuration was backed up.
- [ ] Previous known-good commit and rollback target were recorded.
- [ ] Production environment was explicitly selected.
- [ ] Monitoring and rollback owners are available.

This checklist does not authorize deployment by itself.
