from openmm import unit
from openmm.app import Simulation
from uibcdf_reporters import MolSysMTTrajectoryDictReporter
from uibcdf_reporters import TQDMReporter

def langevin(item, time = None, saving_timestep = None, integration_timestep= 2*unit.femtoseconds,
             friction=1.0/unit.picoseconds, temperature=300.0*unit.kelvin,
             initial_coordinates=None, initial_velocities=None, platform_name='CUDA',
             reporters=None, tqdm=True):

    """Newtonian classical dynamics of a molecular system with OpenMM.

    The trajectory of a newtonian classical dynamics of a molecular system is obtained together with the
    values of potential and kinetic energy. This method is nothing but a short cut to run quick
    molecular dynamics with the test systems of this library by means of OpenMM.

    Parameters
    ----------

    system: openmm.System
        Molecular system as a system class of OpenMM (see: link)
    friction: unit.Quantity
        Damping parameter of the Langevin dynamics (in units of 1/time).
    initial_coordinates: unit.Quantity
        Initial coordinates of the system as a numpy array with shape [n_particles, 3] and units of
        length. Where 'n_particles' is the number of particles of the system.
    initial_velocities: unit.Quantity
        Initial velocities of the system as a numpy array with shape [n_particles, 3] and units of
        length/time. Where 'n_particles' is the number of particles of the system.
    integration_timestep: unit.Quantity
        Time step used by the integrator of the equations of motion. The parameter needs to have
        units of time.
    saving_timestep: unit.Quantity
        Time step used to report the output trajectory. The parameter needs to have units of time.
    total_time: unit.Quantity
        Total runing time of the simulation. The parameter needs to have units of time.
    platform_name: str (default: 'CPU')
        Platform to run the dynamics: 'CPU', 'OPENCL' or 'CUDA' (according to those options to run
        OpenMM, see documentation),
    verbose: bool (default: True)
        Verbose switcher. The method will print out information if the value is True.

    Returns
    -------

    time: unit.Quantity
        Time as numpy array of shape [n_frames] with units of picoseconds.
    position: unit.Quantity
        Positions of the systems particles in every reported frame as numpy array of shape [n_frames, n_particles, 3] with units of nanometers.
    velocity: unit.Quantity
        Velocities of the systems particles in every reported frame as numpy array of shape
        [n_frames, n_particles, 3] with units of nanometers/picoseconds.
    kinetic_energy: unit.Quantity
        Kinetic energy of the system in every reported frame as numpy array of shape
        [n_frames] with units of kilocalories/mole.
    potential_energy: unit.Quantity
        Potential energy of the system in every reported frame as numpy array of shape
        [n_frames] with units of kilocalories/mole.

    Examples
    --------

    >>> from uibcdf_test_systems import DoubleWell
    >>> from uibcdf_test_systems.simulation import newtonian
    >>> from openmm import unit
    >>> double_well = DoubleWell(n_particles = 1, mass = 64 * unit.amu, Eo=4.0 * unit.kilocalories_per_mole, a=1.0 * unit.nanometers, b=0.0 * unit.kilocalories_per_mole))
    >>> initial_coordinates =  np.zeros([1, 3], np.float32) * unit.nanometers
    >>> initial_velocities = np.zeros([1, 3], np.float32) * unit.nanometers/unit.picoseconds
    >>> initial_coordinates[0,0] = 1.0 * unit.nanometers
    >>> time, position, velocity, kinetic_energy, potential_energy = langevin_NVT(double_well,
    >>>                                                                           friction = 0.1/unit.picoseconds,
    >>>                                                                           initial_coordinates = initial_coordinates,
    >>>                                                                           initial_velocities = initial_velocities,
    >>>                                                                           integration_timestep = 0.02 * unit.picoseconds,
    >>>                                                                           saving_timestep = 0.5 * unit.picoseconds,
    >>>                                                                           total_time = 100 * unit.picoseconds)

    Notes
    -----

    See the `corresponding documentation in the user guide regarding this method
        <../../simulations/newtonian.html>`_.

    Some simple examples on how this method is used can be found in the users guide sections
    corresponding to `the free particle <../../systems/free_particle.html>`_, `the harmonic
    well potential <../../systems/harmonic_well_potential.html>`_ or `the double well potential
    <../../systems/double_well_potential.html>`_.

    """

    from openmm import LangevinIntegrator, Platform, Context
    from openmm import unit
    import numpy as np

    # System parameters.
    n_particles = item.system.getNumParticles()

    # Integrator.

    integrator = LangevinIntegrator(temperature, friction, integration_timestep)

    # Platform.

    platform = Platform.getPlatformByName(platform_name)

    # Simulation.

    simulation = Simulation(item.topology, item.system, integrator, platform)

    # Initial Context.

    if initial_coordinates is None:
        if item.coordinates is not None:
            simulation.context.setPositions(item.coordinates)
        else:
            raise SystemWithoutCoordinatesError()
    else:
        simulation.context.setPositions(initial_coordinates)

    if initial_velocities is None:
        if item.velocities is not None:
            simulation.context.setVelocities(item.velocities)
        else:
            raise SystemWithoutVelocitiesError()
    elif initial_velocities=='zeros':
        initial_velocities = np.zeros([n_particles, 3], np.float32) * unit.nanometers/unit.picosecond
        simulation.context.setVelocities(initial_velocities)
    elif initial_velocities=='boltzmann':
        simulation.context.setVelocitiesToTemperature(temperature)
    else:
        simulation.context.setVelocities(initial_velocities)

    # Reporters.

    default_reporter = False
    tqdm_reporter = False

    if reporters is None:
        reporters = []

    if saving_timestep is not None and len(reporters)==0:
        saving_steps_interval = int(saving_timestep/integration_timestep)
        default_reporter = MolSysMTTrajectoryDictReporter(saving_steps_interval, time=True, coordinates=True,
                potentialEnergy=True, kineticEnergy=True, box=True)
        reporters.append(default_reporter)

    for reporter in reporters:
        simulation.reporters.append(reporter)

    # Initial report
    initial_state = simulation.context.getState(getEnergy=True, getPositions=True, getVelocities=True)
    for reporter in reporters:
        reporter.report(simulation, initial_state)

    n_steps = int(time/integration_timestep)
    if tqdm:
        tqdm_reporter = TQDMReporter(100, n_steps)
        simulation.reporters.append(tqdm_reporter)
    simulation.step(n_steps)

    if tqdm_reporter:
        tqdm_reporter.finalize()

    if default_reporter:
        return default_reporter.finalize()
    else:
        pass

