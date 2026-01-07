"""
Domain Agent Registry
Manages domain-specific agent mappings and configurations for scalable domain integration.
"""

import os
from typing import List, Dict, Any

# Domain agent mapping - easily extensible for new domains
DOMAIN_AGENT_MAPPING = {
    # Health & Medical
    'bloodwork_analyzer': ('agents.bloodwork_agent', 'bloodwork_analyzer'),
    'body_composition_analyzer': ('agents.body_comp_agent', 'body_composition_analyzer'),

    # Automotive
    'sales_assistant': ('agents.sales_agent', 'sales_assistant'),
    'maintenance_specialist': ('agents.maintenance_agent', 'maintenance_specialist'),

    # Food & Grocery
    'grocery_assistant': ('agents.grocery_agent', 'grocery_assistant'),
    
    # Future domains - placeholder for easy extension
    # 'grocery_advisor': ('agents.grocery_agent', 'grocery_advisor'),
    # 'fashion_consultant': ('agents.fashion_agent', 'fashion_consultant'),
    # 'automotive_specialist': ('agents.sales_agent', 'sales_specialist'),
    # 'furniture_designer': ('agents.furniture_agent', 'furniture_designer'),
    # 'electronics_expert': ('agents.electronics_agent', 'electronics_expert'),
}

# Domain agent descriptions for prompt generation
DOMAIN_AGENT_DESCRIPTIONS = {
    # Health & Medical
    'bloodwork_analyzer': 'Analyzes laboratory blood test results, extracts lab values, identifies abnormal ranges, and provides medical insights',
    'body_composition_analyzer': 'Analyzes body composition data including weight, body fat %, muscle mass, BMI, and fitness metrics',
    
    # Automotive
    'sales_assistant': 'Assists with vehicle recommendations, automotive product selection, and sales inquiries based on customer needs and preferences',
    'maintenance_specialist': 'Provides vehicle maintenance advice, service recommendations, and automotive care guidance based on vehicle history and usage',
    
    # Food & Grocery
    'grocery_assistant': 'Provides personalized grocery recommendations based on dietary preferences, restrictions, nutrition goals, and shopping habits',
    
    # Future domain descriptions - placeholder for easy extension
    # 'fashion_consultant': 'Offers style advice and clothing recommendations based on body type, preferences, and occasion',
    # 'furniture_designer': 'Helps with home furnishing choices based on space, style preferences, and functional needs',
    # 'electronics_expert': 'Provides technology product recommendations and compatibility guidance for electronic devices',
}

# Domain-specific routing rules for prompt generation
DOMAIN_ROUTING_RULES = {
    'health': {
        'agents': ['bloodwork_analyzer', 'body_composition_analyzer'],
        'routing_queries': [
            'Health data analysis queries ("analyze my bloodwork", "check my body composition")',
            'Medical test result interpretation ("what do these lab values mean")',
            'Fitness and health metric analysis ("evaluate my fitness progress")',
            'Document or image analysis for health data'
        ],
        'coordination_rules': [
            'Use domain agents when queries involve health data analysis',
            'Pass relevant customer data to domain agents when available',
            'Integrate domain agent insights with product recommendations',
            'Synthesize health insights with personalized product suggestions'
        ]
    },
    'automotive': {
        'agents': ['sales_assistant', 'maintenance_specialist'],
        'routing_queries': [
            'Vehicle purchase and sales queries ("recommend a car", "vehicle comparison")',
            'Automotive maintenance questions ("service schedule", "repair advice")',
            'Car specifications and features inquiries ("fuel efficiency", "safety ratings")',
            'Auto parts and accessories recommendations ("brake pads", "tires")'
        ],
        'coordination_rules': [
            'Use automotive agents for vehicle-related inquiries and recommendations',
            'Consider customer driving habits and vehicle history when available',
            'Integrate maintenance schedules with product suggestions',
            'Provide comprehensive automotive solutions combining sales and service advice'
        ]
    },
    'grocery': {
        'agents': ['grocery_assistant'],
        'routing_queries': [
            'Food and nutrition queries ("healthy meal options", "dietary recommendations")',
            'Grocery shopping assistance ("shopping list", "meal planning")',
            'Dietary restriction queries ("gluten-free products", "vegan options")',
            'Nutrition analysis and ingredient recommendations ("protein sources", "vitamin supplements")'
        ],
        'coordination_rules': [
            'Use grocery agent for food, nutrition, and dietary queries',
            'Consider dietary preferences, restrictions, and health goals',
            'Integrate nutritional insights with product recommendations',
            'Provide meal planning and grocery shopping guidance'
        ]
    },
    # Future domain categories - ready for extension
    # 'lifestyle': {
    #     'agents': ['fashion_consultant'],
    #     'routing_queries': [
    #         'Style and fashion requests ("outfit recommendations", "wardrobe essentials")'
    #     ],
    #     'coordination_rules': [
    #         'Consider personal style preferences and body type',
    #         'Integrate fashion advice with product recommendations'
    #     ]
    # },
    # 'electronics': {
    #     'agents': ['electronics_expert'],
    #     'routing_queries': [
    #         'Electronics and tech questions ("device compatibility", "tech specs")'
    #     ],
    #     'coordination_rules': [
    #         'Provide technical specifications and compatibility information',
    #         'Consider technical requirements and user experience level'
    #     ]
    # }
}


def get_enabled_domain_agents() -> List[Any]:
    """Load domain agents based on configuration"""
    enabled_agents = []
    domain_agents_config = os.getenv('DOMAIN_AGENTS', '').strip()
    
    if not domain_agents_config:
        return enabled_agents
    
    agent_names = [name.strip() for name in domain_agents_config.split(',') if name.strip()]
    
    for agent_name in agent_names:
        if agent_name in DOMAIN_AGENT_MAPPING:
            try:
                module_path, function_name = DOMAIN_AGENT_MAPPING[agent_name]
                module = __import__(module_path, fromlist=[function_name])
                agent_function = getattr(module, function_name)
                enabled_agents.append(agent_function)
            except ImportError as e:
                print(f"Warning: Could not import domain agent {agent_name}: {e}")
            except AttributeError as e:
                print(f"Warning: Could not find function {function_name} in {module_path}: {e}")
        else:
            print(f"Warning: Unknown domain agent {agent_name}")
    
    return enabled_agents


def get_enabled_agent_names() -> List[str]:
    """Get list of enabled domain agent names from configuration"""
    domain_agents_config = os.getenv('DOMAIN_AGENTS', '').strip()
    
    if not domain_agents_config:
        return []
    
    return [name.strip() for name in domain_agents_config.split(',') if name.strip()]


def generate_domain_agent_prompt_section() -> str:
    """Generate dynamic prompt section for enabled domain agents"""
    agent_names = get_enabled_agent_names()
    
    if not agent_names:
        return ""
    
    domain_section = "\n### Domain-Specific Agents\nYou also coordinate with these specialized domain agents:\n"
    
    # Add agent descriptions
    for i, agent_name in enumerate(agent_names, 3):
        if agent_name in DOMAIN_AGENT_DESCRIPTIONS:
            domain_section += f"{i}. **{agent_name}** - {DOMAIN_AGENT_DESCRIPTIONS[agent_name]}\n"
    
    # Generate routing rules based on enabled agents
    domain_section += "\n**Route to domain agents for:**\n"
    
    # Group agents by domain category and add relevant routing rules
    for domain_category, config in DOMAIN_ROUTING_RULES.items():
        enabled_agents_in_category = [agent for agent in agent_names if agent in config['agents']]
        if enabled_agents_in_category:
            for query_type in config['routing_queries']:
                domain_section += f"- {query_type}\n"
    
    domain_section += "\n**Domain Agent Coordination:**\n"
    
    # Add coordination rules based on enabled agents
    rule_counter = 1
    for domain_category, config in DOMAIN_ROUTING_RULES.items():
        enabled_agents_in_category = [agent for agent in agent_names if agent in config['agents']]
        if enabled_agents_in_category:
            for rule in config['coordination_rules']:
                domain_section += f"{rule_counter}. {rule}\n"
                rule_counter += 1
    
    domain_section += "\n"
    
    return domain_section


def register_new_domain_agent(agent_name: str, module_path: str, function_name: str, description: str, domain_category: str = None):
    """
    Helper function to register a new domain agent (for future use)
    
    Args:
        agent_name: Unique identifier for the agent
        module_path: Python module path where agent is defined
        function_name: Function name to import from the module
        description: Human-readable description of the agent's capabilities
        domain_category: Optional category to group the agent with others
    """
    DOMAIN_AGENT_MAPPING[agent_name] = (module_path, function_name)
    DOMAIN_AGENT_DESCRIPTIONS[agent_name] = description
    
    # This function provides a programmatic way to add new domain agents
    # without directly modifying the dictionaries above
    print(f"Registered new domain agent: {agent_name}")


def get_all_available_domains() -> List[str]:
    """Get list of all available domain agents"""
    return list(DOMAIN_AGENT_MAPPING.keys())


def get_domain_agent_info(agent_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific domain agent"""
    if agent_name not in DOMAIN_AGENT_MAPPING:
        return {}
    
    module_path, function_name = DOMAIN_AGENT_MAPPING[agent_name]
    description = DOMAIN_AGENT_DESCRIPTIONS.get(agent_name, "No description available")
    
    return {
        'agent_name': agent_name,
        'module_path': module_path,
        'function_name': function_name,
        'description': description,
        'is_enabled': agent_name in get_enabled_agent_names()
    }
