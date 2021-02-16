
import numpy as np


def load_population_data(builder):
    pop_data = builder.data.load('population.structure')
    pop_data = pop_data[['age', 'sex', 'value']].rename(columns={'value': 'population'})
    pop_data['bau_population'] = pop_data['population']
    return pop_data


class BasePopulation:
    """
    This component implements the core population demographics: age, sex,
    population size.

    The configuration options for this component are:

    ``population_size``
        The number of population cohorts (**must be specified**).
    ``max_age``
        The age at which cohorts are removed from the population
        (default: 110).

    .. code-block:: yaml

       configuration
           population:
               population_size: 44 # Male and female 5-year cohorts, 0 to 109.
               max_age: 110        # The age at which cohorts are removed.

    """

    configuration_defaults = {
        'population': {
            'max_age': 110,
        }
    }

    @property
    def name(self):
        return 'base_population'
    
    def setup(self, builder):
        """Load the population data."""
        columns = ['age', 'sex', 'population', 'bau_population',
                   'acmr', 'bau_acmr',
                   'pr_death', 'bau_pr_death', 'deaths', 'bau_deaths',
                   'yld_rate', 'bau_yld_rate',
                   'person_years', 'bau_person_years',
                   'HALY', 'bau_HALY']

        self.pop_data = load_population_data(builder)
        
        # Create additional columns with placeholder (zero) values.
        for column in columns:
            if column in self.pop_data.columns:
                continue
            self.pop_data.loc[:, column] = 0.0

        self.max_age = builder.configuration.population.max_age

        self.start_year = builder.configuration.time.start.year
        self.clock = builder.time.clock()

        # Track all of the quantities that exist in the core spreadsheet table.
        builder.population.initializes_simulants(self.on_initialize_simulants, creates_columns=columns)
        self.population_view = builder.population.get_view(columns + ['tracked'])

        # Age cohorts before each time-step (except the first time-step).
        builder.event.register_listener('time_step__prepare', self.on_time_step_prepare)

    def on_initialize_simulants(self, _):
        """Initialize each cohort."""
        self.population_view.update(self.pop_data)

    def on_time_step_prepare(self, event):
        """Remove cohorts that have reached the maximum age."""
        pop = self.population_view.get(event.index, query='tracked == True')
        # Only increase cohort ages after the first time-step.
        if self.clock().year > self.start_year:
            pop['age'] += 1
        pop.loc[pop.age > self.max_age, 'tracked'] = False
        self.population_view.update(pop)

