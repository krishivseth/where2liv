import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
from google import genai
from google.genai import types
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all specialized agents"""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize base agent with Gemini API"""
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        if self.gemini_api_key:
            self.client = genai.Client(api_key=self.gemini_api_key)
            self.model_name = "gemini-2.5-flash-lite"  # Using Gemini 2.5 Flash Lite
            self.available = True
        else:
            self.client = None
            self.model_name = None
            self.available = False
            logger.warning("Gemini API key not provided - AI features disabled")
        
        self.conversation_history = []
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Get the name of this agent"""
        pass
    
    def generate_response(self, user_input: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AI response using Gemini 2.5 Flash Lite"""
        try:
            if not self.available:
                return {
                    'success': False,
                    'error': 'Gemini AI not available - API key not configured'
                }
            
            # Build context
            context = ""
            if context_data:
                context = f"\nContext Data:\n{json.dumps(context_data, indent=2)}\n\n"
            
            # Create full prompt
            full_prompt = f"{self.get_system_prompt()}\n\n{context}User Query: {user_input}"
            
            # Create content using new API format
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=full_prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0,  # No extra thinking budget for faster responses
                ),
            )
            
            # Generate response using streaming (but collect all chunks)
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
            
            # Store in conversation history
            self.conversation_history.append({
                'timestamp': datetime.now().isoformat(),
                'user_input': user_input,
                'context_data': context_data,
                'ai_response': response_text,
                'agent': self.get_agent_name()
            })
            
            return {
                'success': True,
                'response': response_text,
                'agent': self.get_agent_name(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Gemini AI generation failed for {self.get_agent_name()}: {e}")
            return {
                'success': False,
                'error': f'AI generation failed: {str(e)}',
                'agent': self.get_agent_name()
            }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history for this agent"""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []


class SafetyAgent(BaseAgent):
    """Specialized agent for safety analysis and recommendations"""
    
    def __init__(self, safety_analyzer, gemini_api_key: Optional[str] = None):
        super().__init__(gemini_api_key)
        self.safety_analyzer = safety_analyzer
    
    def get_agent_name(self) -> str:
        return "SafetyAgent"
    
    def get_system_prompt(self) -> str:
        return """You are a Safety Analysis Expert specializing in neighborhood safety assessment for housing decisions. 

Your expertise includes:
- Crime pattern analysis and interpretation
- Safety rating systems and risk assessment  
- Personal safety recommendations for residents
- Neighborhood safety trends and insights
- Safety precautions and best practices

When analyzing safety data, provide:
1. Clear interpretation of crime statistics and safety ratings
2. Practical safety recommendations for residents
3. Context about neighborhood safety trends
4. Specific precautions based on crime types in the area
5. Comparisons to citywide safety averages when possible

Be factual, helpful, and focus on actionable safety insights that help people make informed housing decisions."""
    
    def analyze_safety(self, address: str, borough: str = None, zip_code: str = None, radius_miles: float = 0.1) -> Dict[str, Any]:
        """Perform comprehensive separated safety analysis with AI insights for an address"""
        try:
            # Get separated safety data using the safety analyzer
            separated_data = self.safety_analyzer.get_separated_area_analysis(
                address=address,
                borough=borough,
                zip_code=zip_code,
                radius_miles=radius_miles
            )
            
            # Generate AI insights if available
            if self.available and separated_data:
                enhanced_data = separated_data.copy()
                
                # Generate AI insights for personal safety section
                if separated_data.get('personal_safety', {}).get('available'):
                    safety_prompt = self._create_safety_section_prompt(address, separated_data['personal_safety'], 'personal_safety')
                    safety_ai_response = self.generate_response(safety_prompt, context_data=separated_data['personal_safety'])
                    
                    if safety_ai_response.get('success'):
                        enhanced_data['personal_safety']['ai_insights'] = {
                            'summary': safety_ai_response.get('response', ''),
                            'generated_by': self.get_agent_name(),
                            'timestamp': safety_ai_response.get('timestamp')
                        }
                
                # Generate AI insights for neighborhood quality section
                if separated_data.get('neighborhood_quality', {}).get('available'):
                    neighborhood_prompt = self._create_safety_section_prompt(address, separated_data['neighborhood_quality'], 'neighborhood_quality')
                    neighborhood_ai_response = self.generate_response(neighborhood_prompt, context_data=separated_data['neighborhood_quality'])
                    
                    if neighborhood_ai_response.get('success'):
                        enhanced_data['neighborhood_quality']['ai_insights'] = {
                            'summary': neighborhood_ai_response.get('response', ''),
                            'generated_by': self.get_agent_name(),
                            'timestamp': neighborhood_ai_response.get('timestamp')
                        }
                
                return {
                    'success': True,
                    'data': enhanced_data,
                    'agent': self.get_agent_name()
                }
            
            # Fallback to basic analysis or if AI failed
            return {
                'success': True,
                'data': separated_data,
                'agent': self.get_agent_name()
            }
                
        except Exception as e:
            logger.error(f"Safety analysis failed: {e}")
            return {
                'success': False,
                'error': f'Safety analysis failed: {str(e)}',
                'agent': self.get_agent_name()
            }
    
    def _create_safety_section_prompt(self, address: str, section_data: Dict[str, Any], section_type: str) -> str:
        """Create a focused prompt for generating section-specific insights"""
        
        if not section_data.get('available'):
            return f"No {section_type} data available for {address}."
        
        # Extract key data points
        rating = section_data.get('rating', {})
        grade = rating.get('grade', 'N/A')
        score = rating.get('score', 0)
        total_incidents = section_data.get('metrics', {}).get('total_incidents', 0)
        recent_incidents = section_data.get('metrics', {}).get('recent_incidents', 0)
        
        # Get complaint breakdown
        complaint_breakdown = section_data.get('complaint_breakdown', {})
        top_issues = []
        for category, data in complaint_breakdown.items():
            if data.get('count', 0) > 0:
                top_complaints = data.get('top_complaints', {})
                for issue_type, count in list(top_complaints.items())[:2]:
                    top_issues.append(f"{issue_type} ({count})")
        
        if section_type == 'personal_safety':
            prompt = f"""You are analyzing personal safety for {address} based on police crime data.

CRIME DATA:
- Safety Grade: {grade} (Score: {score}/5.0)
- Total Crime Incidents: {total_incidents}
- Recent Activity: {recent_incidents} incidents in last 90 days
- Key Crime Types: {', '.join(top_issues[:4])}

Generate a SHORT analysis (100-150 words) in this format:

**🚨 PERSONAL SAFETY: Grade {grade}**
[One sentence about what this means for personal security]

**⚠️ CRIME AWARENESS:**
• [Most significant crime concern with prevention advice]
• [Time/location-based safety precaution]

**✅ SAFETY POSITIVES:**
• [Reassuring aspect about crime levels]

**🛡️ PROTECTION TIPS:**
• [Specific crime prevention advice]
• [Personal safety best practice]

Focus on actionable crime prevention and personal safety advice."""

        else:  # neighborhood_quality
            prompt = f"""You are analyzing neighborhood quality for {address} based on 311 service request data.

QUALITY OF LIFE DATA:
- Quality Grade: {grade} (Score: {score}/5.0)
- Total 311 Reports: {total_incidents}
- Recent Activity: {recent_incidents} reports in last 90 days
- Key Issues: {', '.join(top_issues[:4])}

Generate a SHORT analysis (100-150 words) in this format:

**🏘️ NEIGHBORHOOD QUALITY: Grade {grade}**
[One sentence about overall community maintenance and services]

**🔧 COMMON ISSUES:**
• [Most frequent quality of life problem and what it means]
• [Service or maintenance concern to be aware of]

**✅ COMMUNITY STRENGTHS:**
• [Positive aspect of neighborhood maintenance or services]

**💡 LIVING TIPS:**
• [Practical advice for dealing with common issues]
• [How to engage with city services effectively]

Focus on quality of life, community engagement, and practical living advice."""

        return prompt
    
    def _determine_neighborhood_context(self, address: str) -> str:
        """Determine neighborhood type from address for context"""
        address_lower = address.lower()
        
        if any(term in address_lower for term in ['castro', 'market st', 'mission']):
            return "Urban entertainment/commercial district"
        elif any(term in address_lower for term in ['executive', 'park', 'blvd']):
            return "Business/residential area"  
        elif any(term in address_lower for term in ['harrison', 'soma', 'folsom']):
            return "Urban mixed-use district"
        else:
            return "Urban neighborhood"
    
    def _generate_basic_safety_summary(self, safety_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic safety summary without AI"""
        data = safety_data.get('data', {})
        safety_rating = data.get('safety_rating', {})
        
        return {
            'grade': safety_rating.get('grade', 'N/A'),
            'score': safety_rating.get('score', 'N/A'),
            'description': safety_rating.get('description', 'Safety data available'),
            'recommendations': [
                'Review local crime patterns before moving',
                'Consider safety precautions appropriate for the area',
                'Stay informed about neighborhood safety updates'
            ]
        }


class RouteAgent(BaseAgent):
    """Specialized agent for route planning and transportation analysis"""
    
    def __init__(self, route_analyzer, gemini_api_key: Optional[str] = None):
        super().__init__(gemini_api_key)
        self.route_analyzer = route_analyzer
    
    def get_agent_name(self) -> str:
        return "RouteAgent"
    
    def get_system_prompt(self) -> str:
        return """You are a Route Planning and Transportation Expert specializing in safe and efficient urban navigation.

Your expertise includes:
- Route optimization for safety and efficiency
- Public transportation systems and connections
- Walking and cycling route safety assessment
- Traffic patterns and commute analysis
- Accessibility considerations for different transportation modes

When analyzing routes, provide:
1. Safe route recommendations with specific turn-by-turn guidance
2. Alternative route options for different times of day
3. Public transportation connections and schedules
4. Safety considerations for walking/cycling routes
5. Estimated travel times and distances
6. Transportation cost analysis

Focus on practical, safety-conscious route planning that helps residents navigate efficiently and securely."""
    
    def plan_routes(self, origin: str, destination: str, mode: str = 'walking') -> Dict[str, Any]:
        """Plan routes between origin and destination"""
        try:
            # Get route data using the route analyzer
            route_data = self.route_analyzer.get_routes(origin, destination, mode)
            
            if not route_data.get('success'):
                return {
                    'success': False,
                    'error': 'Failed to retrieve route data',
                    'details': route_data
                }
            
            # Generate AI insights if available
            if self.available:
                route_analysis = self.generate_response(
                    f"Analyze route options from {origin} to {destination} using {mode} and provide safety and efficiency recommendations.",
                    context_data=route_data
                )
                
                return {
                    'success': True,
                    'route_data': route_data,
                    'ai_analysis': route_analysis,
                    'agent': self.get_agent_name()
                }
            else:
                # Fallback to basic analysis
                return {
                    'success': True,
                    'route_data': route_data,
                    'basic_analysis': self._generate_basic_route_summary(route_data),
                    'agent': self.get_agent_name()
                }
                
        except Exception as e:
            logger.error(f"Route planning failed: {e}")
            return {
                'success': False,
                'error': f'Route planning failed: {str(e)}',
                'agent': self.get_agent_name()
            }
    
    def _generate_basic_route_summary(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic route summary without AI"""
        return {
            'status': 'Route data retrieved',
            'recommendations': [
                'Review route options for safety and convenience',
                'Consider alternative transportation modes',
                'Check route conditions during different times of day'
            ]
        }


class EnergyAgent(BaseAgent):
    """Specialized agent for energy efficiency and cost analysis"""
    
    def __init__(self, bill_estimator, data_processor, gemini_api_key: Optional[str] = None):
        super().__init__(gemini_api_key)
        self.bill_estimator = bill_estimator
        self.data_processor = data_processor
    
    def get_agent_name(self) -> str:
        return "EnergyAgent"
    
    def get_system_prompt(self) -> str:
        return """You are an Energy Efficiency and Cost Analysis Expert specializing in residential energy consumption and building performance.

Your expertise includes:
- Building energy performance analysis and benchmarking
- Utility cost estimation and rate structure analysis
- Energy efficiency recommendations and upgrades
- Seasonal energy usage patterns and optimization
- ENERGY STAR ratings and green building certifications
- Cost-saving strategies for renters and homeowners

When analyzing energy data, provide:
1. Clear explanation of energy costs and consumption patterns
2. Comparison to similar buildings and city averages
3. Practical energy-saving recommendations
4. Seasonal cost variations and budgeting advice
5. Building efficiency insights and potential improvements
6. Long-term cost projections and savings opportunities

Focus on actionable insights that help people understand and manage their energy costs effectively."""
    
    def analyze_energy_costs(self, address: str, num_rooms: int, building_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze energy costs and efficiency for a property"""
        try:
            # Get energy cost estimates
            if building_data:
                energy_data = self.bill_estimator.estimate_bill(building_data, num_rooms)
            else:
                # Try to find building data first
                # This would need integration with address matching
                return {
                    'success': False,
                    'error': 'Building data required for energy analysis',
                    'agent': self.get_agent_name()
                }
            
            # Generate AI insights if available
            if self.available:
                energy_analysis = self.generate_response(
                    f"Analyze the energy costs and efficiency for a {num_rooms}-room apartment at {address}. Provide cost breakdown and efficiency recommendations.",
                    context_data=energy_data
                )
                
                return {
                    'success': True,
                    'energy_data': energy_data,
                    'ai_analysis': energy_analysis,
                    'agent': self.get_agent_name()
                }
            else:
                # Fallback to basic analysis
                return {
                    'success': True,
                    'energy_data': energy_data,
                    'basic_analysis': self._generate_basic_energy_summary(energy_data),
                    'agent': self.get_agent_name()
                }
            
        except Exception as e:
            logger.error(f"Energy analysis failed: {e}")
            return {
                'success': False,
                'error': f'Energy analysis failed: {str(e)}',
                'agent': self.get_agent_name()
            }
    
    def _generate_basic_energy_summary(self, energy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic energy summary without AI"""
        annual_summary = energy_data.get('annual_summary', {})
        
        return {
            'monthly_estimate': annual_summary.get('average_monthly_bill', 'N/A'),
            'annual_estimate': annual_summary.get('total_bill', 'N/A'),
            'total_kwh': annual_summary.get('total_kwh', 'N/A'),
            'recommendations': [
                'Compare costs with similar properties',
                'Consider energy-efficient appliances',
                'Monitor seasonal usage patterns'
            ]
        }


class PropertyAnalysisCoordinator:
    """Coordinates the three specialized agents for comprehensive property analysis"""
    
    def __init__(self, data_processor, bill_estimator, address_matcher, 
                 safety_analyzer, route_analyzer, gemini_api_key: Optional[str] = None):
        """Initialize coordinator with all required components"""
        self.data_processor = data_processor
        self.bill_estimator = bill_estimator
        self.address_matcher = address_matcher
        
        # Initialize specialized agents
        self.safety_agent = SafetyAgent(safety_analyzer, gemini_api_key)
        self.route_agent = RouteAgent(route_analyzer, gemini_api_key)
        self.energy_agent = EnergyAgent(bill_estimator, data_processor, gemini_api_key)
        
        self.agents = {
            'safety': self.safety_agent,
            'route': self.route_agent,
            'energy': self.energy_agent
            }
    
    def analyze_property(self, address: str, num_rooms: int, 
                        include_safety: bool = True,
                        include_routes: bool = False,
                        destination: str = None,
                        route_mode: str = 'walking') -> Dict[str, Any]:
        """Comprehensive property analysis using all specialized agents"""
        try:
            analysis_start = datetime.now()
            results = {
                'query': {
                    'address': address,
                    'num_rooms': num_rooms,
                    'include_safety': include_safety,
                    'include_routes': include_routes,
                    'destination': destination,
                    'route_mode': route_mode
                },
                'analysis_timestamp': analysis_start.isoformat(),
                'agents_used': [],
                'success': True
            }
            
            # Step 1: Find building data
            building_match = self.address_matcher.find_building(address)
            if not building_match:
                return {
                    'success': False,
                    'error': 'Could not find building data for the specified address'
                }
            
            building_data = building_match
            results['building_data'] = building_data
            
            # Step 2: Energy analysis (always included)
            logger.info("Running energy analysis...")
            energy_result = self.energy_agent.analyze_energy_costs(address, num_rooms, building_data)
            if energy_result.get('success'):
                results['energy_analysis'] = energy_result
                results['agents_used'].append('energy')
            
            # Step 3: Safety analysis (if requested)
            if include_safety:
                logger.info("Running safety analysis...")
                borough = building_data.get('Borough')
                safety_result = self.safety_agent.analyze_safety(address, borough)
                if safety_result.get('success'):
                    results['safety_analysis'] = safety_result
                    results['agents_used'].append('safety')
            
            # Step 4: Route analysis (if requested)
            if include_routes and destination:
                logger.info(f"Running route analysis to {destination}...")
                route_result = self.route_agent.plan_routes(address, destination, route_mode)
                if route_result.get('success'):
                    results['route_analysis'] = route_result
                    results['agents_used'].append('route')
            
            results['analysis_duration'] = (datetime.now() - analysis_start).total_seconds()
            return results
            
        except Exception as e:
            logger.error(f"Property analysis coordination failed: {e}")
            return {
                'success': False,
                'error': f'Property analysis failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name"""
        return self.agents.get(agent_name)
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names"""
        return list(self.agents.keys())
    
    def clear_all_histories(self):
        """Clear conversation history for all agents"""
        for agent in self.agents.values():
            agent.clear_history() 