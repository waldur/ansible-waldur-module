# Ansible module for Waldur

Waldur-based solutions can be managed with Ansible modules to allow provisioning and
management of infrastructure under Waldur through Ansible playbooks.

## Supported functionality

- OpenStack management.
- SLURM HPC management
- Common client for Waldur APIs in Python.

See also: <http://docs.ansible.com/ansible/modules.html>

## Installation

```bash
pip install ansible-waldur-module
```

## Example usage

### Configure an Ansible playbook with parameters

```yaml
  name: Trigger master instance
  waldur_marketplace_os_instance:
    access_token: "{{ access_token }}"
    api_url: "{{ api_url }}"
    flavor: m1.micro
    floating_ip: auto
    image: CentOS 7 x86_64
    name: "{{ instance_name }}"
    project: "OpenStack Project"
    offering: Instance in Tenant
    ssh_key: ssh1.pub
    subnet: vpc-1-tm-sub-net-2
    system_volume_size: 40
    wait: false
```

### Pass parameters to an Ansible playbook

```bash
ANSIBLE_LIBRARY=/usr/share/ansible-waldur/ ansible \
    -m waldur_marketplace_os_instance \
    -a "api_url=https://waldur.example.com/api/ access_token=9036194e1ac54cada3248a8c6b203bf7 name=instance-name project='Project name'" \
    localhost
```

### Running playbook using virtual Python environment

If you've installed Ansible Waldur module to virtual Python environment you need to specify
path to Python interpreter and path to module library along with path to playbook:

```bash
ansible-playbook \
    -e ansible_python_interpreter=/home/user/ansible-env/bin/python \
    -M /home/user/ansible-env/lib/python3.8/site-packages/ \
    playbook.yml
```

## Contributing

1. See general guidelines: <https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html>
2. Install `pre-commit` and `tox`

   ```bash
   pip install tox pre-commit
   pre-commit install
   ```

3. When new module is implemented, don't forget to update `py_modules` section in `setup.py` file.
4. When new module is implemented, it should be covered with tests. Run tests using `tox`

   ```bash
   tox
   ```

5. Module name should consist of three parts separated by underscore: `waldur`, plugin name,
   entity name. For example, `waldur_os_snapshot` refers to OpenStack (OS) as plugin name and snapshot as entity name.
