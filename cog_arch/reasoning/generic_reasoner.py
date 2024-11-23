from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

from .multiattempt_pydantic_models import DecidePatchResponse, PruneResponse

from ..prompts import multi_attempt_prompts as mp


class GenericReasoner(BaseLMReasoning):
    def __init__(
            self,
            name='generic_reasoner',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )

    def multiattempt_decide(self, messages, context):
        """
        Decides whether there is enough information to write a patch based
        """
        pydantic_object = DecidePatchResponse
        parser = PydanticOutputParser(pydantic_object=pydantic_object)
        human_msg = mp.multiattempt_decide_prompt + mp.multiattempt_decide_template.format(
            context=context,
            format_instructions=parser.get_format_instructions()
        )
        out = self.lm_reason(
            messages=messages + [HumanMessage(content=human_msg)],
            pydantic_model=pydantic_object,
            structured=True,
        )
        return out

    def delegate_write_patch(self, messages, context):
        human_msg = mp.delegate_write_patch_prompt + mp.context_template.format(context=context)
        out = self.lm_reason(messages=messages + [HumanMessage(content=human_msg)])
        return out

    def delegate_gather_info(self, messages, context):
        human_msg = mp.delegate_gather_info_prompt + mp.context_template.format(context=context)
        out = self.lm_reason(messages=messages + [HumanMessage(content=human_msg)])
        return out

    def prune_working_mem(self, messages, context):
        pydantic_object = PruneResponse
        parser = PydanticOutputParser(pydantic_object=pydantic_object)
        human_msg = mp.prune_working_mem_prompt.format(
            context=context,
            format_instructions=parser.get_format_instructions()
        )
        out = self.lm_reason(
            messages=messages + [HumanMessage(content=human_msg)],
            pydantic_model=pydantic_object,
            structured=True,
        )
        return out

    def decide_info_to_gather(self, messages, context):
        human_msg = mp.decide_info_to_gather_prompt + mp.context_template.format(context=context)
        out = self.lm_reason(messages=messages + [HumanMessage(content=human_msg)])
        return out
